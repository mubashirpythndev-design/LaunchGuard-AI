"""Escalation rules for LaunchGuard AI safety findings (US3, T094, T096).

Pure rule logic adhering to Constitution 2.I:
Imports nothing from cv/ or agent/.
"""

from __future__ import annotations

from collections.abc import Sequence

from rule_engine.types import Finding, Severity


def apply_cue_escalation(findings: Sequence[Finding]) -> list[Finding]:
    """Apply safety escalation rules across findings evaluated in the same run.

    Rule US3-2 (T094):
    A liquid pool alone is 'warning'. A liquid pool with a fire cue in the same run
    escalates to 'critical' due to catastrophic combustion risk.
    """
    has_fire = any(
        f.check_id == "cue.fire"
        and f.severity in (Severity.WARNING, Severity.CRITICAL)
        and not f.degraded
        for f in findings
    )

    result: list[Finding] = []
    for f in findings:
        if (
            f.check_id == "cue.leak"
            and f.severity == Severity.WARNING
            and not f.degraded
            and has_fire
        ):
            # Escalate liquid pool warning to critical when active fire is co-present
            escalated = Finding(
                module=f.module,
                check_id=f.check_id,
                severity=Severity.CRITICAL,
                message=(
                    "Liquid pooling detected concurrent with active flame indication — "
                    "escalated to critical hazard."
                ),
                confidence=f.confidence,
                metrics=f.metrics,
                overlay=f.overlay,
                step_position=f.step_position,
                degraded=f.degraded,
                low_confidence_critical=f.low_confidence_critical,
                near_threshold_note=f.near_threshold_note,
            )
            result.append(escalated)
        else:
            result.append(f)

    return result
