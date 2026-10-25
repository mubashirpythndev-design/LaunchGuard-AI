"""Cue escalation rule unit tests (T094, US3, FR-015, Constitution 2.I).

Verifies that:
- A liquid pool finding alone remains 'warning' (verdict HOLD).
- A liquid pool with an active fire cue escalates to 'critical' (verdict NO-GO).
"""

from __future__ import annotations

from rule_engine.escalation import apply_cue_escalation
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Verdict,
    validate_finding,
)
from rule_engine.verdict import make_decision


def _make_leak_warning_finding() -> Finding:
    f = Finding(
        module="cv.cues",
        check_id="cue.leak",
        severity=Severity.WARNING,
        message="Liquid pooling detected near vehicle base.",
        confidence=0.85,
        metrics=(
            Measurement(
                name="liquid_pool_area",
                value=0.015,
                unit="ratio",
                threshold=0.01,
            ),
        ),
        overlay=Overlay(
            kind=OverlayKind.BBOX,
            check_id="cue.leak",
            points=((0.2, 0.6), (0.8, 0.9)),
            label="Liquid Pool",
        ),
        step_position=3,
    )
    validate_finding(f)
    return f


def _make_fire_critical_finding() -> Finding:
    f = Finding(
        module="cv.cues",
        check_id="cue.fire",
        severity=Severity.CRITICAL,
        message="Visual evidence of flame near vehicle base.",
        confidence=0.90,
        metrics=(
            Measurement(
                name="flame_coverage_ratio",
                value=0.005,
                unit="ratio",
                threshold=0.0005,
            ),
        ),
        overlay=Overlay(
            kind=OverlayKind.BBOX,
            check_id="cue.fire",
            points=((0.4, 0.5), (0.6, 0.7)),
            label="Flame",
        ),
        step_position=3,
    )
    validate_finding(f)
    return f


def _make_motion_warning_finding() -> Finding:
    f = Finding(
        module="cv.cues",
        check_id="cue.motion",
        severity=Severity.WARNING,
        message="Abnormal motion detected near base.",
        confidence=0.80,
        metrics=(
            Measurement(
                name="motion_pixel_ratio",
                value=0.02,
                unit="ratio",
                threshold=0.005,
            ),
        ),
        overlay=Overlay(
            kind=OverlayKind.BBOX,
            check_id="cue.motion",
            points=((0.1, 0.5), (0.3, 0.8)),
            label="Motion",
        ),
        step_position=3,
    )
    validate_finding(f)
    return f


def test_liquid_pool_alone_remains_warning() -> None:
    """A liquid pool alone produces a warning and yields HOLD verdict."""
    leak_finding = _make_leak_warning_finding()

    escalated = apply_cue_escalation([leak_finding])
    assert len(escalated) == 1
    assert escalated[0].severity == Severity.WARNING
    assert escalated[0].check_id == "cue.leak"

    decision = make_decision([leak_finding])
    assert decision.verdict == Verdict.HOLD
    leak_in_decision = next(f for f in decision.findings if f.check_id == "cue.leak")
    assert leak_in_decision.severity == Severity.WARNING


def test_liquid_pool_with_fire_cue_escalates_to_critical() -> None:
    """A liquid pool concurrent with a fire cue escalates to critical and yields NO-GO verdict."""
    leak_finding = _make_leak_warning_finding()
    fire_finding = _make_fire_critical_finding()

    escalated = apply_cue_escalation([leak_finding, fire_finding])
    assert len(escalated) == 2

    leak_escalated = next(f for f in escalated if f.check_id == "cue.leak")
    assert leak_escalated.severity == Severity.CRITICAL
    assert "flame" in leak_escalated.message.lower() or "critical" in leak_escalated.message.lower()

    decision = make_decision([leak_finding, fire_finding])
    assert decision.verdict == Verdict.NO_GO
    leak_in_decision = next(f for f in decision.findings if f.check_id == "cue.leak")
    assert leak_in_decision.severity == Severity.CRITICAL


def test_liquid_pool_with_motion_alone_does_not_escalate() -> None:
    """Liquid pool with non-fire anomaly (e.g. motion) remains warning."""
    leak_finding = _make_leak_warning_finding()
    motion_finding = _make_motion_warning_finding()

    escalated = apply_cue_escalation([leak_finding, motion_finding])
    leak_res = next(f for f in escalated if f.check_id == "cue.leak")
    assert leak_res.severity == Severity.WARNING
