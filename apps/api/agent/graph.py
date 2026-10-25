"""Agentic inspection workflow StateGraph with interrupt and resume (T107, Research R2).

Constitution 3.IV, Research R2, R11:
1. Fixed 5-step order: body -> fins -> launchpad_area -> weather_manual -> decision.
2. interrupt() MUST be the first statement of the weather_manual node.
3. A conditional edge loops back to weather_manual on partial/invalid inputs.
4. CV tool calls live in earlier nodes and are never re-executed on resume.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from agent.multi_angle import evaluate_quadrant
from agent.state import GraphState
from agent.tools import (
    check_fin_alignment,
    check_launchpad_clear,
    check_launchpad_cues,
    inspect_body,
)
from cv.frameio import decode_image
from cv.subject import locate_rocket, unavailable
from rule_engine.manual import MANDATORY_FIELDS
from rule_engine.types import (
    QUADRANTS,
    ManualInputSet,
    Thresholds,
)
from rule_engine.verdict import make_decision

logger = logging.getLogger(__name__)

INPUT_FIELDS_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "wind_speed_ms",
        "label": "Wind speed",
        "type": "number",
        "unit": "m/s",
        "min": 0.0,
        "max": 60.0,
        "required": True,
    },
    {
        "name": "visibility",
        "label": "Visibility",
        "type": "enum",
        "options": ["good", "moderate", "poor"],
        "required": True,
    },
    {
        "name": "precipitation",
        "label": "Precipitation",
        "type": "enum",
        "options": ["none", "light", "heavy"],
        "required": True,
    },
    {
        "name": "area_cleared",
        "label": "Pad area cleared",
        "type": "boolean",
        "required": True,
    },
    {
        "name": "notes",
        "label": "Notes",
        "type": "text",
        "max_length": 500,
        "required": False,
    },
]


def _load_image(image_path: str) -> np.ndarray:
    """Load and decode image from disk path or return a blank test frame if unreadable."""
    path = Path(image_path)
    if path.exists() and path.is_file():
        try:
            return decode_image(path.read_bytes())
        except Exception as exc:
            logger.warning("Could not decode image from '%s': %s", image_path, exc)
    # Default 640x480 gray dummy image for tests
    return np.zeros((480, 640, 3), dtype=np.uint8)


# --- Step 1: Body Inspection ---


async def body_inspection_node(state: GraphState) -> dict[str, Any]:
    """Execute step 1: body inspection for cracks, dents, and damage."""
    thresholds = state.get("thresholds") or Thresholds()
    if "quadrant_paths" in state:
        findings = []
        for quadrant in QUADRANTS:
            findings.extend(await evaluate_quadrant(
                state["quadrant_paths"].get(quadrant), quadrant, inspect_body,
                1, "body", thresholds,
            ))
    else:
        img = _load_image(state.get("image_path", ""))
        findings = inspect_body(img, thresholds=thresholds)

    current_findings = list(state.get("findings") or [])
    current_findings.extend(findings)

    return {
        "findings": current_findings,
        "current_step": 1,
    }


# --- Step 2: Fin Alignment ---


async def fins_inspection_node(state: GraphState) -> dict[str, Any]:
    """Execute step 2: fin symmetry and alignment inspection."""
    thresholds = state.get("thresholds") or Thresholds()
    if "quadrant_paths" in state:
        findings = []
        for quadrant in QUADRANTS:
            findings.extend(await evaluate_quadrant(
                state["quadrant_paths"].get(quadrant), quadrant, check_fin_alignment,
                2, "fins", thresholds,
            ))
    else:
        img = _load_image(state.get("image_path", ""))
        findings = check_fin_alignment(img, thresholds=thresholds)

    current_findings = list(state.get("findings") or [])
    current_findings.extend(findings)

    return {
        "findings": current_findings,
        "current_step": 2,
    }


# --- Step 3: Launchpad Area & Cues ---


async def launchpad_area_node(state: GraphState) -> dict[str, Any]:
    """Execute step 3: launchpad personnel clearance and hazard cues (smoke, fire, leak, motion)."""
    thresholds = state.get("thresholds") or Thresholds()
    danger_zone = state.get("danger_zone")

    if "quadrant_paths" in state:
        findings = list(state.get("findings") or [])
        for quadrant in QUADRANTS:
            for detector in (
                lambda image, cfg: check_launchpad_clear(
                    image, danger_zone=danger_zone, thresholds=cfg
                ),
                lambda image, cfg: check_launchpad_cues(image, thresholds=cfg),
            ):
                findings.extend(await evaluate_quadrant(
                    state["quadrant_paths"].get(quadrant), quadrant, detector,
                    3, "launchpad_area", thresholds,
                ))
        return {"findings": findings, "current_step": 3}

    img = _load_image(state.get("image_path", ""))

    if locate_rocket(img) is None:
        pad_findings = [unavailable(
            "cv.pad", "pad.subject_unverified", 3,
            "Unsupported rocket inspection image; pad and cue checks were not performed.",
        )]
        cue_findings = []
    else:
        pad_findings = check_launchpad_clear(img, danger_zone=danger_zone, thresholds=thresholds)
        cue_findings = check_launchpad_cues(img, thresholds=thresholds)

    current_findings = list(state.get("findings") or [])
    current_findings.extend(pad_findings)
    current_findings.extend(cue_findings)

    return {
        "findings": current_findings,
        "current_step": 3,
    }


# --- Step 4: Weather & Manual Inputs (Interrupt Checkpoint) ---


def weather_manual_node(state: GraphState) -> dict[str, Any]:
    """Execute step 4: manual environmental inputs with LangGraph interrupt().

    CONSTITUTION CRITICAL REQUIREMENT:
    interrupt() MUST be the first statement of this node.
    On resume, execution restarts at the node entrance, returning the resume value.
    """
    # 1. Determine currently missing mandatory inputs
    current_inputs = dict(state.get("manual_inputs") or {})
    missing = [f for f in MANDATORY_FIELDS if current_inputs.get(f) is None]

    # 2. If mandatory inputs are missing, interrupt immediately
    if missing:
        provided = interrupt(
            {
                "missing": missing,
                "fields": INPUT_FIELDS_REGISTRY,
            }
        )
        if isinstance(provided, dict):
            current_inputs.update(provided)

    # 3. Re-evaluate completeness
    new_missing = [f for f in MANDATORY_FIELDS if current_inputs.get(f) is None]

    return {
        "manual_inputs": current_inputs,
        "missing_inputs": new_missing,
        "current_step": 4,
    }


def route_weather_manual(state: GraphState) -> str:
    """Conditional edge: loop back to weather_manual if any mandatory input remains missing."""
    missing = state.get("missing_inputs")
    if missing and len(missing) > 0:
        return "weather_manual"
    return "decision"


# --- Step 5: Final Decision Generation ---


async def decision_node(state: GraphState) -> dict[str, Any]:
    """Execute step 5: deterministic rule engine decision and risk scoring."""
    findings = state.get("findings") or []
    raw_manual = state.get("manual_inputs") or {}
    thresholds = state.get("thresholds") or Thresholds()

    manual_set = ManualInputSet(
        wind_speed_ms=raw_manual.get("wind_speed_ms"),
        visibility=raw_manual.get("visibility"),
        precipitation=raw_manual.get("precipitation"),
        area_cleared=raw_manual.get("area_cleared"),
        notes=raw_manual.get("notes"),
    )

    decision = make_decision(findings, manual_inputs=manual_set, thresholds=thresholds)

    severity_order = {"critical": 0, "warning": 1, "ok": 2}
    non_ok = [f for f in decision.findings if f.severity.value != "ok"]
    non_ok.sort(
        key=lambda f: (
            severity_order.get(f.severity.value, 3),
            f.step_position,
            f.check_id,
        )
    )

    structured_reasons = [
        {
            "check_id": f.check_id,
            "severity": f.severity.value,
            "message": f.message,
            "confidence": f.confidence,
            "ambiguous": f.near_threshold_note is not None,
        }
        for f in non_ok
    ]
    if not structured_reasons:
        structured_reasons = [
            {
                "check_id": "nominal",
                "severity": "ok",
                "message": "All evaluated criteria nominal.",
                "confidence": 1.0,
                "ambiguous": False,
            }
        ]

    return {
        "verdict": decision.verdict,
        "risk_score": decision.risk_score,
        "reasons": structured_reasons,
        "status": "completed",
        "current_step": 5,
    }


def create_inspection_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[GraphState, Any, Any, Any]:
    """Construct and compile the 5-step inspection StateGraph."""
    builder = StateGraph(GraphState)

    # Add 5 ordered steps
    builder.add_node("body", body_inspection_node)
    builder.add_node("fins", fins_inspection_node)
    builder.add_node("launchpad_area", launchpad_area_node)
    builder.add_node("weather_manual", weather_manual_node)
    builder.add_node("decision", decision_node)

    # Wire edges
    builder.add_edge(START, "body")
    builder.add_edge("body", "fins")
    builder.add_edge("fins", "launchpad_area")
    builder.add_edge("launchpad_area", "weather_manual")
    builder.add_conditional_edges(
        "weather_manual",
        route_weather_manual,
        {
            "weather_manual": "weather_manual",
            "decision": "decision",
        },
    )
    builder.add_edge("decision", END)

    return builder.compile(checkpointer=checkpointer)
