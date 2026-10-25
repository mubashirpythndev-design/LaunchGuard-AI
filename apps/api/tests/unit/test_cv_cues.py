"""Launchpad hazard cue detection unit tests (T093, US3, FR-015, Constitution 2.III).

Tests pure functions in cv/cues.py across flame, smoke, liquid pool, motion,
and clean static frames. Asserts finding shape matches all other finding types.
"""

from __future__ import annotations

from pathlib import Path

import cv2

from cv.cues import (
    detect_cues,
    detect_flame,
    detect_leak,
    detect_motion,
    detect_smoke,
)
from cv.frameio import decode_image
from rule_engine.config import MIN_CONFIDENCE_FOR_OK
from rule_engine.types import (
    Finding,
    OverlayKind,
    Severity,
    validate_finding,
)


def _assert_finding_shape_consistent(f: Finding, expected_check_id: str) -> None:
    """Assert finding conforms to Constitution 2.III invariants and matches common finding shape."""
    validate_finding(f)
    assert f.module == "cv.cues"
    assert f.check_id == expected_check_id
    assert isinstance(f.severity, Severity)
    assert 0.0 <= f.confidence <= 1.0
    assert len(f.metrics) >= 1
    assert f.overlay is not None
    assert f.step_position == 3
    for m in f.metrics:
        assert m.name and m.unit
        assert isinstance(m.value, (int, float))


def test_detect_flame_anomalous_frame(fixtures_dir: Path) -> None:
    """Flame region triggers cue.fire critical finding with bounding overlay."""
    normal_path = fixtures_dir / "normal.jpg"
    img = decode_image(normal_path.read_bytes())
    # Draw fire region: BGR = (20, 120, 245) -> bright orange/red
    cv2.rectangle(img, (200, 150), (320, 260), (20, 120, 245), -1)

    findings = detect_flame(img)
    assert len(findings) == 1
    f = findings[0]
    _assert_finding_shape_consistent(f, "cue.fire")

    assert f.severity == Severity.CRITICAL
    assert f.confidence >= 0.75
    assert f.overlay is not None
    assert f.overlay.kind == OverlayKind.BBOX
    assert "flame" in f.message.lower() or "fire" in f.message.lower()


def test_detect_smoke_anomalous_frame(fixtures_dir: Path) -> None:
    """Smoke plume region triggers cue.smoke warning finding with bounding overlay."""
    normal_path = fixtures_dir / "normal.jpg"
    img = decode_image(normal_path.read_bytes())
    # Draw smoke region: grayish, low saturation, moderate luminance (BGR ~ 160, 160, 160)
    cv2.circle(img, (320, 140), 75, (160, 160, 160), -1)
    cv2.circle(img, (380, 110), 60, (170, 170, 170), -1)

    findings = detect_smoke(img)
    assert len(findings) == 1
    f = findings[0]
    _assert_finding_shape_consistent(f, "cue.smoke")

    assert f.severity == Severity.WARNING
    assert f.confidence >= 0.70
    assert f.overlay is not None
    assert f.overlay.kind == OverlayKind.BBOX
    assert "smoke" in f.message.lower() or "vapor" in f.message.lower()


def test_detect_leak_pooling_frame(fixtures_dir: Path) -> None:
    """Liquid pooling on pad deck triggers cue.leak warning finding."""
    normal_path = fixtures_dir / "normal.jpg"
    img = decode_image(normal_path.read_bytes())
    h = img.shape[0]
    # Draw dark puddle on the lower pad deck (y > 0.4 * h)
    cv2.ellipse(img, (300, int(h * 0.75)), (120, 40), 0, 0, 360, (25, 25, 25), -1)

    findings = detect_leak(img)
    assert len(findings) == 1
    f = findings[0]
    _assert_finding_shape_consistent(f, "cue.leak")

    assert f.severity == Severity.WARNING
    assert f.confidence >= 0.75
    assert f.overlay is not None
    assert f.overlay.kind == OverlayKind.BBOX
    assert "liquid" in f.message.lower() or "leak" in f.message.lower()


def test_detect_motion_differencing_frames(fixtures_dir: Path) -> None:
    """Frame differencing between consecutive frames detects abnormal base movement."""
    normal_path = fixtures_dir / "normal.jpg"
    frame1 = decode_image(normal_path.read_bytes())
    frame2 = frame1.copy()
    # Draw displaced object in frame 2
    cv2.rectangle(frame2, (250, 180), (350, 260), (240, 240, 240), -1)

    findings = detect_motion(frame2, reference_img=frame1)
    assert len(findings) == 1
    f = findings[0]
    _assert_finding_shape_consistent(f, "cue.motion")

    assert f.severity == Severity.WARNING
    assert f.overlay is not None
    assert f.overlay.kind == OverlayKind.BBOX
    assert "movement" in f.message.lower() or "motion" in f.message.lower()


def test_clean_static_frame_returns_all_ok(fixtures_dir: Path) -> None:
    """A clean static nominal frame produces OK findings across all four cue checks."""
    normal_path = fixtures_dir / "normal.jpg"
    img = decode_image(normal_path.read_bytes())

    findings = detect_cues(img)
    assert len(findings) == 4

    check_ids = {f.check_id for f in findings}
    assert check_ids == {"cue.fire", "cue.smoke", "cue.leak", "cue.motion"}

    for f in findings:
        _assert_finding_shape_consistent(f, f.check_id)
        assert f.severity == Severity.OK
        assert f.confidence >= MIN_CONFIDENCE_FOR_OK
        assert f.step_position == 3
