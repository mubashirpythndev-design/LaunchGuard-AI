"""Graph state definitions for agentic inspection workflow (T106, Research R2, R11).

Defines the TypedDict holding immutable execution state across the 5 checklist steps.
"""

from __future__ import annotations

from typing import Any, TypedDict

from rule_engine.types import Finding, Quadrant, Thresholds, Verdict


class GraphState(TypedDict, total=False):
    """Execution state passed through the LangGraph StateGraph.

    Maintains run identification, image source, evaluated findings,
    manual inputs, checklist statuses, and final rule engine verdict.
    """

    run_id: str
    image_path: str
    rocket_id: str
    quadrant_paths: dict[Quadrant, str | None]
    danger_zone: list[tuple[float, float]] | None
    thresholds: Thresholds
    findings: list[Finding]
    manual_inputs: dict[str, Any]
    missing_inputs: list[str]
    verdict: Verdict | None
    risk_score: int | None
    reasons: list[dict[str, Any]]
    recommended_actions: list[dict[str, str]]
    report_id: str | None
    status: str
    current_step: int
