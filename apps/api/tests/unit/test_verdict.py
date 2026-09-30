import pytest

from rule_engine import (
    Finding,
    ManualInputSet,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Verdict,
    decide_verdict,
    make_decision,
)


def mk_finding(check_id: str, severity: Severity, conf: float = 1.0) -> Finding:
    overlay = (
        Overlay(kind=OverlayKind.BBOX, check_id=check_id, points=((0.1, 0.1), (0.2, 0.2)))
        if check_id
        not in (
            "zone.occupancy",
            "manual.wind",
            "manual.visibility",
            "manual.precipitation",
            "manual.area_cleared",
        )
        else None
    )
    return Finding(
        module="cv.body"
        if "body" in check_id
        else "cv.fins"
        if "fin" in check_id
        else "rule_engine.manual",
        check_id=check_id,
        severity=severity,
        message=f"Finding for {check_id}",
        confidence=conf,
        metrics=(Measurement(name="metric", value=1.0, unit="unit"),),
        overlay=overlay,
        step_position=1 if "body" in check_id else 2 if "fin" in check_id else 4,
    )


@pytest.mark.parametrize(
    "sevs,expected",
    [
        ([], Verdict.GO),
        ([Severity.OK, Severity.OK], Verdict.GO),
        ([Severity.WARNING], Verdict.HOLD),
        ([Severity.OK, Severity.WARNING, Severity.OK], Verdict.HOLD),
        ([Severity.CRITICAL], Verdict.NO_GO),
        ([Severity.WARNING, Severity.CRITICAL], Verdict.NO_GO),
        ([Severity.CRITICAL, Severity.OK], Verdict.NO_GO),
    ],
)
def test_verdict_matrix(sevs: list[Severity], expected: Verdict) -> None:
    findings = [mk_finding(f"body.cracks_{i}", s) for i, s in enumerate(sevs)]
    assert decide_verdict(findings) == expected


def test_missing_mandatory_inputs_forces_hold(no_network: None) -> None:
    findings = [mk_finding("body.cracks", Severity.OK)]
    decision = make_decision(findings, manual_inputs=ManualInputSet())
    assert decision.verdict == Verdict.HOLD
    assert len(decision.missing_inputs) == 4
    assert any("missing" in r.lower() for r in decision.reasons)


def test_complete_inputs_nominal_gives_go(no_network: None) -> None:
    findings = [mk_finding("body.cracks", Severity.OK)]
    inputs = ManualInputSet(
        wind_speed_ms=4.0,
        visibility="good",
        precipitation="none",
        area_cleared=True,
    )
    decision = make_decision(findings, manual_inputs=inputs)
    assert decision.verdict == Verdict.GO
    assert len(decision.missing_inputs) == 0


def test_critical_finding_overrides_all_to_no_go(no_network: None) -> None:
    findings = [
        mk_finding("body.cracks", Severity.OK),
        mk_finding("fin.alignment", Severity.CRITICAL),
    ]
    inputs = ManualInputSet(
        wind_speed_ms=3.0,
        visibility="good",
        precipitation="none",
        area_cleared=True,
    )
    decision = make_decision(findings, manual_inputs=inputs)
    assert decision.verdict == Verdict.NO_GO
    assert decision.reasons[0] == "Finding for fin.alignment"
