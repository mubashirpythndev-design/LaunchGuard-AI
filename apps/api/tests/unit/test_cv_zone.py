"""Unit tests for cv/zone.py containment logic (T075, FR-012, FR-016).

Verifies the containment rule:
Any overlap (fully inside, edge overlap, corner overlap, or polygon vertex enclosure)
counts as inside the danger zone.
"""

from __future__ import annotations

from cv.zone import determine_zone_status, is_bbox_inside_polygon
from rule_engine.types import Finding, Severity


def test_bbox_inside_outside_and_overlap() -> None:
    """Assert inside, outside, edge overlap, and vertex containment behavior."""
    # Standard square zone [0.2, 0.2] to [0.8, 0.8]
    zone = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]

    # 1. Fully inside
    bbox_inside = (0.3, 0.3, 0.5, 0.5)
    assert is_bbox_inside_polygon(bbox_inside, zone) is True

    # 2. Fully outside (top right)
    bbox_outside = (0.85, 0.85, 0.95, 0.95)
    assert is_bbox_inside_polygon(bbox_outside, zone) is False

    # 3. Fully outside (left)
    bbox_left = (0.05, 0.3, 0.15, 0.5)
    assert is_bbox_inside_polygon(bbox_left, zone) is False

    # 4. Edge overlap: box crosses left boundary x=0.2
    bbox_cross_left = (0.1, 0.3, 0.3, 0.5)
    assert is_bbox_inside_polygon(bbox_cross_left, zone) is True

    # 5. Edge overlap: box crosses bottom boundary y=0.8
    bbox_cross_bottom = (0.4, 0.7, 0.6, 0.9)
    assert is_bbox_inside_polygon(bbox_cross_bottom, zone) is True

    # 6. Corner touch: corner touching vertex at (0.2, 0.2)
    bbox_corner_touch = (0.1, 0.1, 0.2, 0.2)
    assert is_bbox_inside_polygon(bbox_corner_touch, zone) is True

    # 7. Large box enclosing entire polygon
    bbox_enclosing = (0.1, 0.1, 0.9, 0.9)
    assert is_bbox_inside_polygon(bbox_enclosing, zone) is True


def test_concave_polygon_containment() -> None:
    """Test containment with a non-convex (concave) danger zone."""
    # U-shaped or notched polygon
    zone = [
        [0.2, 0.2],
        [0.8, 0.2],
        [0.8, 0.8],
        [0.5, 0.5],  # Inward notch
        [0.2, 0.8],
    ]

    # Inside one of the outer lobes
    bbox_lobe = (0.25, 0.3, 0.45, 0.5)
    assert is_bbox_inside_polygon(bbox_lobe, zone) is True

    # Sitting inside the notch (outside the polygon)
    bbox_notch = (0.48, 0.65, 0.52, 0.75)
    assert is_bbox_inside_polygon(bbox_notch, zone) is False


def test_determine_zone_status() -> None:
    """Assert zone status reflects CLEAR, WARNING, and DANGER based on finding severities."""
    assert determine_zone_status([]) == "CLEAR"

    ok_finding = Finding(
        module="cv.launchpad_area",
        check_id="zone.occupancy",
        severity=Severity.OK,
        message="Launchpad clear",
        confidence=0.9,
    )
    assert determine_zone_status([ok_finding]) == "CLEAR"

    warn_finding = Finding(
        module="cv.launchpad_area",
        check_id="zone.warning",
        severity=Severity.WARNING,
        message="Personnel near perimeter",
        confidence=0.8,
    )
    assert determine_zone_status([ok_finding, warn_finding]) == "WARNING"

    crit_finding = Finding(
        module="cv.launchpad_area",
        check_id="zone.occupancy",
        severity=Severity.CRITICAL,
        message="Personnel in danger zone",
        confidence=0.95,
    )
    assert determine_zone_status([ok_finding, warn_finding, crit_finding]) == "DANGER"
