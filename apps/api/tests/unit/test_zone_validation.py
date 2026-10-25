"""Unit tests for danger zone polygon validation (T076, FR-012, FR-013).

Verifies that malformed polygons are rejected with specific, descriptive messages:
- Fewer than 3 points
- Zero-area polygon (collinear or coincident points)
- Self-intersecting outline (bow-tie or complex crossover)
"""

from __future__ import annotations

import pytest

from cv.zone import validate_zone_polygon


def test_valid_polygon_passes() -> None:
    """A valid triangle and convex/concave quadrilateral pass validation."""
    triangle = [[0.1, 0.1], [0.5, 0.9], [0.8, 0.2]]
    validate_zone_polygon(triangle)

    quad = [[0.2, 0.2], [0.7, 0.2], [0.8, 0.8], [0.1, 0.7]]
    validate_zone_polygon(quad)


def test_polygon_fewer_than_three_points_rejected() -> None:
    """Polygons with 0, 1, or 2 points are rejected with a clear message."""
    with pytest.raises(ValueError, match="at least 3 points"):
        validate_zone_polygon([])

    with pytest.raises(ValueError, match="at least 3 points"):
        validate_zone_polygon([[0.5, 0.5]])

    with pytest.raises(ValueError, match="at least 3 points"):
        validate_zone_polygon([[0.2, 0.2], [0.8, 0.8]])


def test_zero_area_polygon_rejected() -> None:
    """Collinear or duplicate points producing zero area are rejected."""
    # Collinear horizontal points
    collinear = [[0.1, 0.5], [0.4, 0.5], [0.9, 0.5]]
    with pytest.raises(ValueError, match="zero area"):
        validate_zone_polygon(collinear)

    # Identical points
    identical = [[0.3, 0.3], [0.3, 0.3], [0.3, 0.3]]
    with pytest.raises(ValueError, match="zero area"):
        validate_zone_polygon(identical)


def test_self_intersecting_polygon_rejected() -> None:
    """A polygon whose edges cross over each other is rejected."""
    # Classic bow-tie figure-8
    bowtie = [
        [0.1, 0.1],
        [0.9, 0.9],
        [0.1, 0.9],
        [0.9, 0.1],
    ]
    with pytest.raises(ValueError, match="self-intersecting"):
        validate_zone_polygon(bowtie)
