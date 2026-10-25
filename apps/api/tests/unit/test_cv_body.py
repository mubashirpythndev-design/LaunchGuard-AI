"""Unit and fixture tests for cv/body.py (T052, FR-009, SC-005, Constitution 5.II)."""

import cv2

from cv.body import inspect_body
from rule_engine.config import MIN_CONFIDENCE_FOR_OK
from rule_engine.types import Severity, validate_finding
from tests.conftest import FIXTURES_IMAGES


def test_cv_body_pass_fixture(no_network: None) -> None:
    """Fixture with an intact rocket yields ok findings for cracks, dents, damage,
    and burn marks."""
    pass_path = FIXTURES_IMAGES / "body.cracks__pass.jpg"
    assert pass_path.exists(), f"Pass fixture missing at {pass_path}"

    img = cv2.imread(str(pass_path))
    assert img is not None, "Failed to read pass fixture image"

    findings = inspect_body(img)
    assert len(findings) >= 4, "Expected findings for cracks, dents, damage, and burn marks"

    check_ids = {f.check_id for f in findings}
    assert "body.cracks" in check_ids
    assert "body.dents" in check_ids
    assert "body.damage" in check_ids
    assert "body.burn_marks" in check_ids

    for f in findings:
        validate_finding(f)
        assert f.severity == Severity.OK, (
            f"Expected OK severity on intact fixture, got {f.severity} for {f.check_id}"
        )
        assert f.confidence >= MIN_CONFIDENCE_FOR_OK, (
            f"Confidence {f.confidence} below OK floor {MIN_CONFIDENCE_FOR_OK}"
        )
        assert len(f.metrics) > 0
        assert f.overlay is not None


def test_cv_body_fail_fixture(no_network: None) -> None:
    """Fixture with body anomalies yields at least one warning/critical finding."""
    fail_path = FIXTURES_IMAGES / "body.cracks__fail.jpg"
    assert fail_path.exists(), f"Fail fixture missing at {fail_path}"

    img = cv2.imread(str(fail_path))
    assert img is not None, "Failed to read fail fixture image"

    findings = inspect_body(img)
    assert len(findings) >= 4

    for f in findings:
        validate_finding(f)

    non_ok = [f for f in findings if f.severity in (Severity.WARNING, Severity.CRITICAL)]
    assert len(non_ok) > 0, (
        "Expected at least one warning or critical finding on defective body fixture"
    )

    # Check that defective finding message is hedged and descriptive
    defect = non_ok[0]
    assert defect.confidence >= 0.0
    assert defect.overlay is not None
    assert any(
        term in defect.message.lower()
        for term in ("crack", "dent", "damage", "burn", "defect", "anomaly", "surface")
    )
