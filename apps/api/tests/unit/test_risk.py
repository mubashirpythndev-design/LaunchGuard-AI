import random

from rule_engine import (
    Finding,
    Measurement,
    Severity,
    Verdict,
    compute_risk_score,
    risk_band,
)


def mk_f(sev: Severity, conf: float) -> Finding:
    return Finding(
        module="cv.body",
        check_id="body.cracks",
        severity=sev,
        message="m",
        confidence=conf,
        metrics=(Measurement(name="m", value=1.0, unit="u"),),
        step_position=1,
    )


def test_risk_score_bands() -> None:
    # GO band: 0–30
    assert compute_risk_score([], Verdict.GO) == 0
    assert compute_risk_score([mk_f(Severity.OK, 0.2)], Verdict.GO) <= 30

    # HOLD band: 40–69
    assert 40 <= compute_risk_score([mk_f(Severity.WARNING, 0.5)], Verdict.HOLD) <= 69
    assert 40 <= compute_risk_score([mk_f(Severity.WARNING, 1.0)] * 10, Verdict.HOLD) <= 69

    # NO-GO band: 70–100
    assert 70 <= compute_risk_score([mk_f(Severity.CRITICAL, 0.5)], Verdict.NO_GO) <= 100
    assert compute_risk_score([mk_f(Severity.CRITICAL, 1.0)] * 5, Verdict.NO_GO) == 100


def test_risk_band_labels() -> None:
    assert risk_band(10) == "low"
    assert risk_band(30) == "low"
    assert risk_band(40) == "elevated"
    assert risk_band(69) == "elevated"
    assert risk_band(70) == "severe"
    assert risk_band(100) == "severe"


def test_risk_score_order_independence() -> None:
    findings = [
        mk_f(Severity.WARNING, 0.8),
        mk_f(Severity.WARNING, 0.4),
        mk_f(Severity.OK, 0.2),
        mk_f(Severity.CRITICAL, 0.9),
    ]
    s1 = compute_risk_score(findings, Verdict.NO_GO)
    shuffled = list(findings)
    random.seed(42)
    random.shuffle(shuffled)
    s2 = compute_risk_score(shuffled, Verdict.NO_GO)
    assert s1 == s2
