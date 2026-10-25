"""Unit and fixture tests for cv/fins.py (T053, FR-011, FR-043, SC-002, Constitution 5.II)."""

import cv2

from cv.fins import check_fin_alignment, evaluate_fin_deviation
from rule_engine.config import MIN_CONFIDENCE_FOR_OK
from rule_engine.types import (
    OverlayKind,
    Severity,
    Thresholds,
    is_threshold_ambiguous,
    validate_finding,
)
from tests.conftest import FIXTURES_IMAGES


def test_cv_fins_pass_fixture(no_network: None) -> None:
    """Intact fin fixture measures within tolerance and yields OK."""
    pass_path = FIXTURES_IMAGES / "fin.alignment__pass.jpg"
    assert pass_path.exists(), f"Pass fixture missing at {pass_path}"

    img = cv2.imread(str(pass_path))
    assert img is not None, "Failed to read fin pass fixture"

    findings = check_fin_alignment(img)
    assert len(findings) == 1, "Expected single fin.alignment finding"
    f = findings[0]
    validate_finding(f)

    assert f.check_id == "fin.alignment"
    assert f.severity == Severity.OK
    assert f.confidence >= MIN_CONFIDENCE_FOR_OK
    assert f.overlay is not None
    assert f.overlay.kind == OverlayKind.ARC

    # Assert measurement properties
    dev_m = next((m for m in f.metrics if m.name == "fin_angle_deviation"), None)
    assert dev_m is not None
    assert dev_m.unit == "deg"
    assert dev_m.error_margin == 1.5
    assert dev_m.value <= 3.0


def test_cv_fins_fail_fixture(no_network: None) -> None:
    """Misaligned fin fixture yields warning or critical."""
    fail_path = FIXTURES_IMAGES / "fin.alignment__fail.jpg"
    assert fail_path.exists(), f"Fail fixture missing at {fail_path}"

    img = cv2.imread(str(fail_path))
    assert img is not None, "Failed to read fin fail fixture"

    findings = check_fin_alignment(img)
    assert len(findings) == 1
    f = findings[0]
    validate_finding(f)

    assert f.check_id == "fin.alignment"
    assert f.severity in (Severity.WARNING, Severity.CRITICAL)
    assert f.overlay is not None
    assert f.overlay.kind == OverlayKind.ARC

    dev_m = next((m for m in f.metrics if m.name == "fin_angle_deviation"), None)
    assert dev_m is not None
    assert dev_m.value > 3.0


def test_fin_threshold_boundaries_and_error_margin() -> None:
    """FR-011 & FR-043: Boundaries at exactly 3.0° and 6.0° fall on less-severe side."""
    thresholds = Thresholds(
        fin_angle_warning_deg=3.0,
        fin_angle_critical_deg=6.0,
        fin_angle_error_margin_deg=1.5,
    )

    # Exactly 0.0 -> OK
    f0 = evaluate_fin_deviation(0.0, thresholds)
    assert f0.severity == Severity.OK

    # Exactly 3.0° falls on less-severe side (OK), with ambiguity flagged because |3.0 - 3.0| <= 1.5
    f3 = evaluate_fin_deviation(3.0, thresholds)
    assert f3.severity == Severity.OK
    assert f3.near_threshold_note is not None
    dev_m3 = next(m for m in f3.metrics if m.name == "fin_angle_deviation")
    assert is_threshold_ambiguous(dev_m3) is True

    # 3.1° strictly exceeds 3.0° -> WARNING
    f3_1 = evaluate_fin_deviation(3.1, thresholds)
    assert f3_1.severity == Severity.WARNING

    # Exactly 6.0° falls on less-severe side (WARNING)
    f6 = evaluate_fin_deviation(6.0, thresholds)
    assert f6.severity == Severity.WARNING
    assert f6.near_threshold_note is not None

    # 6.1° strictly exceeds 6.0° -> CRITICAL
    f6_1 = evaluate_fin_deviation(6.1, thresholds)
    assert f6_1.severity == Severity.CRITICAL
