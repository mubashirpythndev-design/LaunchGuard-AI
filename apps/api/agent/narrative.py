"""Narrative generation and no-image-bytes guarantee (T108, Research R11, FR-026, FR-039).

Builds a text-only NarrativeContext DTO strictly from an allow-list of fields.
Guarantees zero image data, pixel coordinates, base64 strings, or file paths reach the LLM.
Calls gpt-4o-mini with a 6-second timeout and fails safely to the template path.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from openai import AsyncOpenAI

from db.models import NarrativeStatus
from rule_engine.types import Finding, Reason, Verdict

logger = logging.getLogger(__name__)

DENYLIST_SUBSTRINGS = (
    "data:image",
    "base64",
    "image/jpeg",
    "image/png",
    "image/webp",
    ".jpg",
    ".png",
    ".webp",
    "/media/",
    "\\media\\",
)


@dataclass(frozen=True)
class MetricNarrativeContext:
    """Allow-listed metric values for narrative generation."""

    name: str
    value: float
    unit: str
    threshold: float | None = None


@dataclass(frozen=True)
class FindingNarrativeContext:
    """Allow-listed finding fields for narrative generation (excludes overlays and file paths)."""

    check_id: str
    severity: str
    message: str
    confidence: float
    metrics: tuple[MetricNarrativeContext, ...] = ()
    step_position: int = 0
    near_threshold_note: str | None = None


@dataclass(frozen=True)
class NarrativeContext:
    """Structured, text-only safety report context for language model explanation.

    Strictly constructed via field allow-list. Excludes:
    - Raw image bytes or base64 data
    - Image MIME types or file paths
    - Pixel coordinates and bounding boxes
    """

    verdict: str
    risk_score: int
    reasons: tuple[str, ...]
    findings: tuple[FindingNarrativeContext, ...]


@dataclass(frozen=True)
class NarrativeResult:
    """Validated language model response or graceful fallback."""

    status: NarrativeStatus
    text: str | None
    model: str | None
    recommended_actions: list[dict[str, str]] | None = None


def build_narrative_context(
    verdict: Verdict,
    risk_score: int,
    reasons: Sequence[Reason | dict[str, Any] | str],
    findings: Sequence[Finding],
) -> NarrativeContext:
    """Extract allow-listed fields from decision and findings into NarrativeContext."""
    extracted_reasons: list[str] = []
    for r in reasons:
        if isinstance(r, str):
            extracted_reasons.append(r)
        elif isinstance(r, dict):
            msg = r.get("message")
            if msg:
                extracted_reasons.append(str(msg))
        else:
            extracted_reasons.append(r.message)

    extracted_findings: list[FindingNarrativeContext] = []
    for f in findings:
        metric_contexts = tuple(
            MetricNarrativeContext(
                name=m.name,
                value=m.value,
                unit=m.unit,
                threshold=m.threshold,
            )
            for m in f.metrics
        )
        extracted_findings.append(
            FindingNarrativeContext(
                check_id=f.check_id,
                severity=f.severity.value,
                message=f.message,
                confidence=round(f.confidence, 2),
                metrics=metric_contexts,
                step_position=f.step_position,
                near_threshold_note=f.near_threshold_note,
            )
        )

    return NarrativeContext(
        verdict=verdict.value,
        risk_score=risk_score,
        reasons=tuple(extracted_reasons),
        findings=tuple(extracted_findings),
    )


def serialize_narrative_payload(context: NarrativeContext) -> str:
    """Serialize NarrativeContext to JSON string for prompt injection."""
    return json.dumps(asdict(context), indent=2)


def validate_payload_safety(payload_json: str) -> None:
    """Assert that payload contains no denylisted image indicators or filesystem paths."""
    lower_payload = payload_json.lower()
    for token in DENYLIST_SUBSTRINGS:
        if token in lower_payload:
            raise ValueError(f"Prohibited substring '{token}' found in narrative payload.")

    import re

    # Match Windows drive letter paths (e.g. C:\ or D:/)
    if re.search(r"[a-zA-Z]:[\\/]", payload_json):
        raise ValueError("Absolute Windows path found in narrative payload.")


NARRATIVE_SYSTEM_PROMPT = """You are LaunchGuard AI Safety Narrative Assistant.
Your task is to write an objective, technical executive summary explaining the evaluation.

Requirements:
1. Explain the findings clearly in 1-2 concise paragraphs.
2. Hedged language: Use 'appears', 'possible', 'measured' for sensor observations.
3. Recommend specific corrective actions for each non-ok finding.
4. Output MUST be valid JSON adhering to this exact schema:
{
  "narrative": "Detailed technical explanation...",
  "recommended_actions": [
    {"check_id": "...", "action": "Specific remediation step"}
  ]
}
Do NOT include any verdict field in your response. The verdict is immutable and fixed by rules.
"""


async def generate_narrative(
    context: NarrativeContext,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    timeout_sec: float = 6.0,
) -> NarrativeResult:
    """Call language model with strict timeout and fall back to template path on failure."""
    if not api_key:
        logger.info("OPENAI_API_KEY not configured; using template fallback.")
        return NarrativeResult(
            status=NarrativeStatus.UNAVAILABLE,
            text=None,
            model=None,
            recommended_actions=None,
        )

    payload_json = serialize_narrative_payload(context)
    validate_payload_safety(payload_json)

    client = AsyncOpenAI(api_key=api_key, timeout=timeout_sec)
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Here is the safety inspection context:\n\n{payload_json}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        parsed = json.loads(content)

        narrative_text = str(parsed.get("narrative", "")).strip()
        raw_actions = parsed.get("recommended_actions", [])
        actions: list[dict[str, str]] = []
        if isinstance(raw_actions, list):
            for a in raw_actions:
                if isinstance(a, dict) and "check_id" in a and "action" in a:
                    actions.append({"check_id": str(a["check_id"]), "action": str(a["action"])})

        if not narrative_text:
            return NarrativeResult(
                status=NarrativeStatus.UNAVAILABLE,
                text=None,
                model=None,
                recommended_actions=None,
            )

        return NarrativeResult(
            status=NarrativeStatus.AVAILABLE,
            text=narrative_text,
            model=model,
            recommended_actions=actions if actions else None,
        )
    except Exception as exc:
        logger.warning(
            "Narrative generation failed or timed out (%s); falling back to template path.", exc
        )
        return NarrativeResult(
            status=NarrativeStatus.UNAVAILABLE,
            text=None,
            model=None,
            recommended_actions=None,
        )
