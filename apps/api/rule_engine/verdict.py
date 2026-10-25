"""Deterministic launch decision engine (Constitution 2.I, Research R6).

The ONLY producer of GO / HOLD / NO-GO verdicts.
Imports nothing from cv/ or agent/.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from rule_engine.config import apply_confidence_floor
from rule_engine.escalation import apply_cue_escalation
from rule_engine.manual import evaluate_manual_inputs, get_missing_mandatory_inputs
from rule_engine.risk import compute_risk_score
from rule_engine.types import (
    Decision,
    Finding,
    ManualInputSet,
    Severity,
    StepResult,
    Thresholds,
    Verdict,
    validate_finding,
)

MODULE_ACTIONS: dict[str, str] = {
    "body": "Reinspect the flagged body section and capture a close-up image.",
    "fins": "Reinspect fin mounts and re-measure alignment with the camera side-on.",
    "launchpad_area": (
        "Clear the launch exclusion zone and confirm with range safety before proceeding."
    ),
    "pad": "Clear the launch exclusion zone and confirm with range safety before proceeding.",
    "hazard": "Investigate the flagged smoke, flame, or leak indication before proceeding.",
    "cue": "Investigate the flagged smoke, flame, or leak indication before proceeding.",
    "weather_manual": (
        "Resolve the flagged environmental or procedural condition before proceeding."
    ),
    "manual": "Resolve the flagged environmental or procedural condition before proceeding.",
    "reference": (
        "Re-capture the flagged quadrant and inspect the changed surface against its golden "
        "reference."
    ),
}


def _build_checklist(
    findings: Sequence[Finding],
    missing_inputs: Sequence[str],
    verdict: Verdict,
) -> tuple[StepResult, ...]:
    def step_info(pos: int) -> tuple[Literal["passed", "failed", "blocked"], int]:
        step_f = [f for f in findings if f.step_position == pos]
        count = len(step_f)
        if any(f.severity in (Severity.CRITICAL, Severity.WARNING) for f in step_f):
            return "failed", count
        return "passed", count

    s1_status, s1_count = step_info(1)
    s2_status, s2_count = step_info(2)
    s3_status, s3_count = step_info(3)
    s4_status, s4_count = step_info(4)
    if missing_inputs:
        s4_status = "blocked"

    s5_status: Literal["passed", "failed"] = "passed" if verdict == Verdict.GO else "failed"

    return (
        StepResult(position=1, step_key="body", status=s1_status, finding_count=s1_count),
        StepResult(position=2, step_key="fins", status=s2_status, finding_count=s2_count),
        StepResult(
            position=3,
            step_key="launchpad_area",
            status=s3_status,
            finding_count=s3_count,
        ),
        StepResult(
            position=4,
            step_key="weather_manual",
            status=s4_status,
            finding_count=s4_count,
        ),
        StepResult(position=5, step_key="decision", status=s5_status, finding_count=0),
    )


def decide_verdict(
    findings: Sequence[Finding],
    missing_inputs: Sequence[str] = (),
) -> Verdict:
    """Compute the deterministic verdict from evaluated findings and input completeness.

    Order:
    1. Any finding critical -> NO-GO
    2. Any finding warning OR missing mandatory inputs -> HOLD
    3. Otherwise -> GO
    """
    if any(f.severity == Severity.CRITICAL for f in findings):
        return Verdict.NO_GO
    if any(f.severity == Severity.WARNING for f in findings) or len(missing_inputs) > 0:
        return Verdict.HOLD
    return Verdict.GO


def make_decision(
    cv_findings: Sequence[Finding],
    manual_inputs: ManualInputSet | None = None,
    thresholds: Thresholds | None = None,
    computed_at: datetime | None = None,
) -> Decision:
    """Evaluate all findings, apply confidence floor, and generate final Decision."""
    if computed_at is None:
        computed_at = datetime.now(UTC)

    # 1. Apply fail-safe confidence floor and validate each finding
    processed_findings: list[Finding] = []
    for f in cv_findings:
        floored = apply_confidence_floor(f)
        validate_finding(floored)
        processed_findings.append(floored)

    # 2. Evaluate manual inputs
    manual_eval = evaluate_manual_inputs(manual_inputs)
    for mf in manual_eval:
        validate_finding(mf)
        processed_findings.append(mf)

    missing_inputs = get_missing_mandatory_inputs(manual_inputs)

    # 2.5 Apply deterministic escalation rules across findings (US3, T094)
    processed_findings = apply_cue_escalation(processed_findings)

    # 3. Deterministic verdict
    verdict = decide_verdict(processed_findings, missing_inputs)

    # 4. Advisory risk score (0–100)
    risk_score = compute_risk_score(processed_findings, verdict)

    # 5. Extract structured reasons (ordered: CRITICAL first, then WARNING, then position)
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.OK: 2}
    non_ok_findings = [f for f in processed_findings if f.severity != Severity.OK]
    non_ok_findings.sort(key=lambda f: (severity_order[f.severity], f.step_position, f.check_id))

    reasons: list[str] = [f.message for f in non_ok_findings]
    if not reasons:
        reasons = [
            "All evaluated hardware, pad safety, and environmental criteria verified nominal."
        ]

    # 6. Derive recommended actions (deduplicated)
    actions: list[str] = []
    seen_actions: set[str] = set()
    for f in non_ok_findings:
        # Match module key prefix
        key = f.module.split(".")[-1]
        action = MODULE_ACTIONS.get(key) or MODULE_ACTIONS.get(f.module)
        if not action:
            # Fallback based on check_id prefix
            check_prefix = f.check_id.split(".")[0]
            action = MODULE_ACTIONS.get(
                check_prefix, "Perform visual reinspection of the flagged anomaly."
            )
        if action and action not in seen_actions:
            seen_actions.add(action)
            actions.append(action)

    if not actions:
        actions = ["Proceed with standard countdown procedure under safety officer oversight."]

    checklist = _build_checklist(processed_findings, missing_inputs, verdict)

    return Decision(
        verdict=verdict,
        risk_score=risk_score,
        findings=tuple(processed_findings),
        checklist=checklist,
        reasons=tuple(reasons),
        recommended_actions=tuple(actions),
        missing_inputs=tuple(missing_inputs),
        computed_at=computed_at,
    )
