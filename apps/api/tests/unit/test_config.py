from rule_engine import (
    Finding,
    Measurement,
    Severity,
    apply_confidence_floor,
)


def mk_finding(sev: Severity, conf: float) -> Finding:
    return Finding(
        module="cv.fins",
        check_id="fin.alignment",
        severity=sev,
        message="Fin measurement",
        confidence=conf,
        metrics=(Measurement(name="angle", value=45.0, unit="deg"),),
        step_position=2,
    )


def test_confidence_floor_promotes_ok_to_warning() -> None:
    f = mk_finding(Severity.OK, 0.34)
    floored = apply_confidence_floor(f)
    assert floored.severity == Severity.WARNING
    assert "floor" in floored.message.lower()


def test_confidence_floor_preserves_acceptable_ok() -> None:
    f = mk_finding(Severity.OK, 0.35)
    floored = apply_confidence_floor(f)
    assert floored.severity == Severity.OK

    f2 = mk_finding(Severity.OK, 0.90)
    assert apply_confidence_floor(f2).severity == Severity.OK


def test_confidence_floor_never_downgrades_critical_or_warning() -> None:
    crit = mk_finding(Severity.CRITICAL, 0.10)
    floored_crit = apply_confidence_floor(crit)
    assert floored_crit.severity == Severity.CRITICAL

    warn = mk_finding(Severity.WARNING, 0.15)
    floored_warn = apply_confidence_floor(warn)
    assert floored_warn.severity == Severity.WARNING


def test_apply_confidence_floor_never_returns_ok_below_threshold() -> None:
    for conf_int in range(0, 35):
        conf = conf_int / 100.0
        f = mk_finding(Severity.OK, conf)
        floored = apply_confidence_floor(f)
        assert floored.severity != Severity.OK
        assert floored.severity == Severity.WARNING
