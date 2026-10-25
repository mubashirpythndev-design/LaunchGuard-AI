"""Unit tests for cv/failsafe.py wrapper (T054, FR-005, NFR-003, Constitution 2.II)."""

import time
from typing import Any

from cv.failsafe import failsafe
from rule_engine.types import Finding, Measurement, Severity, validate_finding


def test_empty_detector_results_are_degraded_not_silent() -> None:
    @failsafe(module="cv.body", name="Empty check", check_id="body.damage")
    def empty() -> list[Finding]:
        return []

    finding = empty()[0]
    assert finding.severity == Severity.WARNING and finding.degraded


def test_low_confidence_ok_is_never_returned_as_ok() -> None:
    @failsafe(module="cv.body", name="Uncertain check", check_id="body.damage")
    def uncertain() -> list[Finding]:
        return [Finding(
            module="cv.body", check_id="body.damage", severity=Severity.OK,
            message="Uncertain", confidence=0.1,
            metrics=(Measurement("sample", 1, "count"),),
        )]

    finding = uncertain()[0]
    assert finding.severity == Severity.WARNING and finding.degraded
    assert finding.confidence == 0.1


def test_failsafe_handles_exception() -> None:
    """A module forced to raise yields severity='warning', confidence=0.0, degraded=True."""

    @failsafe(module="cv.body", name="Body integrity", check_id="body.damage", step_position=1)
    def crashing_detector(*args: Any, **kwargs: Any) -> list[Finding]:
        raise RuntimeError("Simulated CV segmentation fault or model crash")

    findings = crashing_detector(None)
    assert len(findings) == 1
    f = findings[0]
    validate_finding(f)

    assert f.severity == Severity.WARNING
    assert f.confidence == 0.0
    assert f.degraded is True
    assert f.module == "cv.body"
    assert f.check_id == "body.damage"
    assert (
        "could not be evaluated" in f.message.lower()
        or "manual check required" in f.message.lower()
    )
    assert any(m.name in ("error", "status") for m in f.metrics)


def test_failsafe_handles_timeout() -> None:
    """A module forced to hang/timeout yields severity='warning', confidence=0.0, degraded=True."""

    @failsafe(
        module="cv.fins",
        name="Fin alignment",
        check_id="fin.alignment",
        step_position=2,
        timeout_s=0.1,
    )
    def hanging_detector(*args: Any, **kwargs: Any) -> list[Finding]:
        time.sleep(0.5)
        return [
            Finding(
                module="cv.fins",
                check_id="fin.alignment",
                severity=Severity.OK,
                message="Normal",
                confidence=0.9,
                metrics=(Measurement(name="fin_angle_deviation", value=0.5, unit="deg"),),
            )
        ]

    findings = hanging_detector(None)
    assert len(findings) == 1
    f = findings[0]
    validate_finding(f)

    assert f.severity == Severity.WARNING
    assert f.confidence == 0.0
    assert f.degraded is True
    assert f.module == "cv.fins"
    assert f.check_id == "fin.alignment"
    assert "timeout" in f.message.lower() or "could not be evaluated" in f.message.lower()
