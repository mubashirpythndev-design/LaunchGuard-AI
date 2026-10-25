"""Danger zone polygon geometry and containment evaluation (T082, FR-012, FR-016).

Tests normalized bounding boxes against user-defined danger zone polygons using
cv2.pointPolygonTest and segment intersection. Enforces the non-negotiable rule
that any overlap (including partial or edge overlap) counts as inside the zone.
"""

from __future__ import annotations

import cv2
import numpy as np

from rule_engine.types import Finding, Severity


def _ccw(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Counter-clockwise cross product test for points a, b, c."""
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_properly_intersect(
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    p4: tuple[float, float],
) -> bool:
    """Return True if line segment p1-p2 strictly intersects p3-p4."""
    d1 = _ccw(p3, p4, p1)
    d2 = _ccw(p3, p4, p2)
    d3 = _ccw(p1, p2, p3)
    d4 = _ccw(p1, p2, p4)

    eps = 1e-7
    if ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and (
        (d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps)
    ):
        return True
    return False


def validate_zone_polygon(points: list[list[float]] | list[tuple[float, float]]) -> None:
    """Validate danger zone polygon geometry according to safety rules.

    Raises ValueError with descriptive reason if polygon is malformed:
    - Fewer than 3 points
    - Zero area
    - Self-intersecting outline
    """
    if len(points) < 3:
        raise ValueError("Danger zone polygon must contain at least 3 points.")

    pts = [(float(p[0]), float(p[1])) for p in points]
    n = len(pts)

    # 1. Check for self-intersecting edges
    for i in range(n):
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        for j in range(i + 1, n):
            # Non-adjacent edges only
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            p3 = pts[j]
            p4 = pts[(j + 1) % n]
            if _segments_properly_intersect(p1, p2, p3, p4):
                raise ValueError("Danger zone polygon outline is self-intersecting.")

    # 2. Check for zero or negative area via Shoelace formula
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    shoelace_area = abs(area) * 0.5

    if shoelace_area <= 1e-7:
        raise ValueError("Danger zone polygon has zero area.")


def is_bbox_inside_polygon(
    bbox_norm: tuple[float, float, float, float] | list[float],
    polygon_norm: list[list[float]] | list[tuple[float, float]],
) -> bool:
    """Test if a normalized bounding box overlaps with a normalized polygon.

    Rule FR-012 / Containment rule:
    Any overlap — complete containment, corner containment, center containment,
    polygon vertex inside bbox, or boundary edge intersection — counts as inside.
    """
    x1, y1, x2, y2 = bbox_norm[0], bbox_norm[1], bbox_norm[2], bbox_norm[3]
    min_x, max_x = min(x1, x2), max(x1, x2)
    min_y, max_y = min(y1, y2), max(y1, y2)

    poly_pts = np.array(polygon_norm, dtype=np.float32)
    if poly_pts.ndim != 2 or poly_pts.shape[0] < 3:
        return False

    # 1. Test the 4 corners of the bounding box with cv2.pointPolygonTest
    corners = [
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    ]
    for c in corners:
        test = cv2.pointPolygonTest(poly_pts, (float(c[0]), float(c[1])), measureDist=False)
        if test >= 0:  # Inside or on edge
            return True

    # 2. Test center of the bounding box
    center = ((min_x + max_x) * 0.5, (min_y + max_y) * 0.5)
    test_center = cv2.pointPolygonTest(
        poly_pts, (float(center[0]), float(center[1])), measureDist=False
    )
    if test_center >= 0:
        return True

    # 3. Test if any polygon vertex is enclosed within the bounding box
    for p in polygon_norm:
        px, py = float(p[0]), float(p[1])
        if min_x <= px <= max_x and min_y <= py <= max_y:
            return True

    # 4. Test edge intersections between the 4 bbox segments and polygon segments
    bbox_segments = [
        (corners[0], corners[1]),
        (corners[1], corners[2]),
        (corners[2], corners[3]),
        (corners[3], corners[0]),
    ]
    num_poly = len(polygon_norm)
    for b1, b2 in bbox_segments:
        for i in range(num_poly):
            p1 = (float(polygon_norm[i][0]), float(polygon_norm[i][1]))
            p2 = (
                float(polygon_norm[(i + 1) % num_poly][0]),
                float(polygon_norm[(i + 1) % num_poly][1]),
            )
            if _segments_properly_intersect(b1, b2, p1, p2):
                return True

    return False


def determine_zone_status(findings: list[Finding]) -> str:
    """Determine live zone status (CLEAR, WARNING, DANGER) from active findings."""
    for f in findings:
        if f.severity == Severity.CRITICAL:
            return "DANGER"
    for f in findings:
        if f.severity == Severity.WARNING:
            return "WARNING"
    return "CLEAR"
