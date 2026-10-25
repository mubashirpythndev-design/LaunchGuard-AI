"""Fixture-style tests for golden-reference alignment and deviation measurements."""

from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from cv.reference import analyze_reference, compare_reference
from rule_engine.types import Severity


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("rocket_current_intact.jpg", Severity.OK), ("rocket_current_cracked.jpg", Severity.CRITICAL)],
)
def test_shipped_demo_fixtures_are_reproducible(
    fixtures_dir: Path, filename: str, expected: Severity
) -> None:
    baseline_path = fixtures_dir / "rocket_golden_reference.jpg"
    current_path = fixtures_dir / filename
    assert baseline_path.read_bytes() == (fixtures_dir / "rocket_reference_front.jpg").read_bytes()
    assert (fixtures_dir / "rocket_current_cracked.jpg").read_bytes() == (
        fixtures_dir / "rocket_current_damaged.jpg"
    ).read_bytes()
    web_demo = Path(__file__).resolve().parents[3] / "web" / "public" / "demo"
    for fixture in (baseline_path, current_path):
        assert fixture.read_bytes() == (web_demo / fixture.name).read_bytes()
    reference = cv2.imread(str(baseline_path))
    current = cv2.imread(str(current_path))
    assert reference is not None and current is not None
    assert reference.shape == current.shape == (600, 800, 3)
    first = compare_reference(reference, current, "back")
    second = compare_reference(reference, current, "back")
    assert first == second
    assert first.severity == expected
    assert not first.degraded
    assert first.overlay is not None
    metrics = {metric.name: metric.value for metric in first.metrics}
    if expected == Severity.CRITICAL:
        assert metrics["deviation_area_pct"] > 2.0
        # Evidence must mark the central synthetic defect, not a frame-edge
        # artifact introduced by interpolation or SSIM's neighborhood window.
        assert all(0.35 < x < 0.7 and 0.25 < y < 0.8 for x, y in first.overlay.points)
    else:
        assert metrics["deviation_area_pct"] == 0.0


def reference_frame() -> NDArray[np.uint8]:
    """Create a repeatable, feature-rich rocket surface with an existing decal."""
    image = np.full((720, 960, 3), 38, dtype=np.uint8)
    cv2.rectangle(image, (245, 55), (715, 680), (184, 190, 196), -1)
    cv2.rectangle(image, (265, 75), (695, 660), (214, 218, 222), 3)
    for x in range(285, 690, 55):
        for y in range(105, 645, 55):
            color = (70 + (x + y) % 80, 85 + x % 65, 95 + y % 55)
            cv2.circle(image, (x, y), 8, color, -1)
            cv2.line(image, (x - 14, y + 13), (x + 14, y + 13), (105, 105, 105), 2)
    cv2.putText(image, "LG-27", (370, 350), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (35, 35, 35), 5)
    cv2.rectangle(image, (305, 470), (455, 535), (48, 82, 158), -1)
    cv2.putText(image, "BASE", (320, 515), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (235, 235, 235), 2)
    return image


def test_identical_reference_is_ok() -> None:
    reference = reference_frame()
    result = analyze_reference(reference, reference.copy(), "front")
    assert result.finding.severity == Severity.OK
    assert not result.finding.degraded
    assert result.aligned_current is not None
    assert result.heatmap_bgr is not None
    metrics = {metric.name: metric.value for metric in result.finding.metrics}
    assert metrics["deviation_area_pct"] < 0.5
    assert metrics["ssim_score"] > 0.99


def test_existing_decal_in_both_images_is_ignored_after_alignment() -> None:
    reference = reference_frame()
    matrix = cv2.getRotationMatrix2D((480, 360), 7.0, 0.96)
    current = cv2.warpAffine(reference, matrix, (960, 720), borderValue=(38, 38, 38))
    finding = compare_reference(reference, current, "right")
    assert finding.severity == Severity.OK
    assert finding.check_id == "reference.structural_deviation"


def test_new_surface_damage_is_critical_with_overlay() -> None:
    reference = reference_frame()
    current = reference.copy()
    cv2.line(current, (350, 180), (610, 530), (8, 8, 8), 25)
    cv2.circle(current, (565, 250), 55, (15, 15, 15), -1)
    finding = compare_reference(reference, current, "back")
    assert finding.severity == Severity.CRITICAL
    assert finding.overlay is not None
    assert finding.overlay.check_id == "reference.structural_deviation"
    assert "appears" in finding.message.lower() or "possible" in finding.message.lower()
    metrics = {metric.name: metric.value for metric in finding.metrics}
    assert metrics["deviation_area_pct"] > 2.0


def test_misaligned_or_featureless_frame_degrades_to_warning() -> None:
    reference = reference_frame()
    current = np.full_like(reference, 127)
    finding = compare_reference(reference, current, "left")
    assert finding.severity == Severity.WARNING
    assert finding.degraded
    assert finding.confidence == 0.0
    assert finding.check_id == "reference.alignment_failed"
