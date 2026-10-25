"""Report assembly, early persistence, and narrative attachment (T109, SH-006, SH-008).

Constitution 2.I & Research R11:
1. Assembles and writes the 'reports' row with narrative_status='pending' BEFORE
   the language model is invoked.
2. The verdict, risk score, checklist, and reasons are fixed by deterministic rules
   and can never be modified by the language model.
3. Subsequent narrative completion updates ONLY the narrative columns.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.narrative import NarrativeResult
from app.config import MANDATED_DISCLAIMER
from db.models import NarrativeStatus, ReportModel
from db.repo import get_report_by_run, upsert_report
from rule_engine.registry import STEP_MAP
from rule_engine.types import Decision, Finding, Severity

logger = logging.getLogger(__name__)


def build_structured_reasons(findings: list[Finding]) -> list[dict[str, Any]]:
    """Build structured reasons ordered by CRITICAL first, then WARNING, then step position."""
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.OK: 2}
    non_ok = [f for f in findings if f.severity != Severity.OK]
    non_ok.sort(key=lambda f: (severity_order[f.severity], f.step_position, f.check_id))

    if not non_ok:
        return [
            {
                "check_id": "nominal",
                "severity": "ok",
                "message": (
                    "All evaluated hardware, pad safety, and environmental criteria "
                    "verified nominal."
                ),
                "confidence": 1.0,
                "ambiguous": False,
            }
        ]

    return [
        {
            "check_id": f.check_id,
            "severity": f.severity.value,
            "message": f.message,
            "confidence": f.confidence,
            "ambiguous": f.near_threshold_note is not None,
        }
        for f in non_ok
    ]


def build_structured_actions(
    findings: list[Finding], default_actions: tuple[str, ...]
) -> list[dict[str, str]]:
    """Derive recommended remediation actions mapped to specific check IDs."""
    non_ok = [f for f in findings if f.severity != Severity.OK]
    if not non_ok:
        return [
            {
                "check_id": "nominal",
                "action": (
                    "Proceed with standard countdown procedure under safety officer oversight."
                ),
            }
        ]

    actions: list[dict[str, str]] = []
    seen: set[str] = set()

    for idx, f in enumerate(non_ok):
        action_text = (
            default_actions[idx]
            if idx < len(default_actions)
            else f"Reinspect and verify anomaly for check '{f.check_id}'."
        )
        if f.check_id not in seen:
            seen.add(f.check_id)
            actions.append({"check_id": f.check_id, "action": action_text})

    return actions


def build_structured_checklist(decision: Decision) -> list[dict[str, Any]]:
    """Serialize checklist steps with stable labels and finding counts."""
    return [
        {
            "position": s.position,
            "step_key": s.step_key,
            "label": str(STEP_MAP.get(s.position, {}).get("label", s.step_key)),
            "status": s.status,
            "finding_count": s.finding_count,
        }
        for s in decision.checklist
    ]


async def assemble_early_report(
    session: AsyncSession,
    run_id: str,
    decision: Decision,
    annotated_ref: str | None = None,
    disclaimer: str = MANDATED_DISCLAIMER,
) -> ReportModel:
    """Write the initial report row before language model narrative generation.

    Guarantees that verdict, risk score, checklist, and reasons are immutably persisted
    and available even if narrative generation fails or times out.
    """
    findings_list = list(decision.findings)
    reasons = build_structured_reasons(findings_list)
    actions = build_structured_actions(findings_list, decision.recommended_actions)
    checklist = build_structured_checklist(decision)

    report = await upsert_report(
        session=session,
        run_id=run_id,
        verdict=decision.verdict,
        risk_score=decision.risk_score,
        reasons=reasons,  # type: ignore[arg-type]
        checklist=checklist,
        recommended_actions=actions,  # type: ignore[arg-type]
        disclaimer=disclaimer,
        narrative_status=NarrativeStatus.PENDING,
        narrative_text=None,
        narrative_model=None,
        annotated_ref=annotated_ref,
    )
    await session.commit()
    return report


async def complete_report_narrative(
    session: AsyncSession,
    run_id: str,
    narrative_result: NarrativeResult,
) -> ReportModel:
    """Update report row with generated narrative or mark unavailable.

    Touches narrative columns ONLY; leaves verdict, risk score, checklist, and reasons untouched.
    """
    report = await get_report_by_run(session, run_id)
    if not report:
        raise ValueError(f"Report for run '{run_id}' not found.")

    report.narrative_status = narrative_result.status
    report.narrative_text = narrative_result.text
    report.narrative_model = narrative_result.model

    if (
        narrative_result.recommended_actions
        and narrative_result.status == NarrativeStatus.AVAILABLE
    ):
        report.recommended_actions_json = list(narrative_result.recommended_actions)

    await session.commit()
    return report
