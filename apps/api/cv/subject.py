"""Conservative geometric applicability check, not a trained rocket classifier.

Only an upright, unobscured side view with two walls, a converging nose and
paired fins is supported. No centered ROI or filename-based fallback exists.
Unsupported views must abstain; this is not proof of semantic object identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import cv2
import numpy as np

from cv.frameio import assess_frame_quality
from rule_engine.types import Finding, Measurement, Severity


@dataclass(frozen=True)
class RocketGeometry:
    body: tuple[int, int, int, int]
    # Measured leading edge endpoints: attachment, outer tip.
    left_fin: tuple[tuple[int, int], tuple[int, int]]
    right_fin: tuple[tuple[int, int], tuple[int, int]]
    confidence: float = 0.6


def unavailable(module: str, check_id: str, step: int, reason: str) -> Finding:
    return Finding(
        module=module, check_id=check_id, step_position=step,
        severity=Severity.WARNING, confidence=0.0, degraded=True,
        message=f"{reason} No defect or fin-angle measurement was made; "
        "manual inspection required.",
        metrics=(Measurement("evaluated", 0.0, "status"),),
    )


def locate_rocket(image: np.ndarray) -> RocketGeometry | None:
    """Require corroborating geometry before any image region is called a vehicle."""
    nominal, _, _ = assess_frame_quality(image)
    if not nominal:
        return None
    height, width = image.shape[:2]
    edges = cv2.Canny(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 40, 120)
    raw = cv2.HoughLinesP(
        edges, 1, np.pi / 180, 25,
        minLineLength=max(15, int(height * 0.035)), maxLineGap=max(5, int(height * 0.015)),
    )
    if raw is None:
        return None
    lines = [tuple(map(int, line)) for line in raw.reshape(-1, 4)]
    walls: dict[int, list[tuple[int, int]]] = {}
    tolerance = max(3, int(width * 0.008))
    for ax, ay, bx, by in lines:
        if abs(ax - bx) > min(tolerance, abs(ay - by) * 0.04):
            continue
        if abs(ay - by) < height * 0.035:
            continue
        x = (ax + bx) // 2
        key = next((key for key in walls if abs(key - x) <= tolerance), x)
        walls.setdefault(key, []).append((min(ay, by), max(ay, by)))
    candidates: list[RocketGeometry] = []
    for x1 in sorted(walls):
        for x2 in sorted(walls):
            bw = x2 - x1
            if not width * 0.025 <= bw <= width * 0.3:
                continue
            y1 = max(min(a for a, _ in walls[x1]), min(a for a, _ in walls[x2]))
            y2 = min(max(b for _, b in walls[x1]), max(b for _, b in walls[x2]))
            bh = y2 - y1
            if bh < max(height * 0.2, bw * 2.5):
                continue
            center = (x1 + x2) / 2
            nose: list[list[tuple[int, int]]] = [[], []]
            fins: list[list[tuple[tuple[int, int], tuple[int, int]]]] = [[], []]
            for ax, ay, bx, by in lines:
                for (rx, ry), (tx, ty) in [((ax, ay), (bx, by)), ((bx, by), (ax, ay))]:
                    for side, wall in enumerate((x1, x2)):
                        if abs(rx - wall) > bw * 0.18:
                            continue
                        if abs(ry - y1) < bh * 0.15 and ty < y1 - bh * 0.2:
                            if abs(tx - center) < bw * 0.25:
                                nose[side].append((tx, ty))
                        outward = wall - tx if side == 0 else tx - wall
                        if y1 + bh * 0.55 < ry <= y2 + bh * 0.06:
                            if bw * 0.25 < outward < bw * 1.5 and ry < ty < y2:
                                fins[side].append(((rx, ry), (tx, ty)))
            common_tip = any(
                hypot(lx - rx, ly - ry) < bw * 0.3
                for lx, ly in nose[0] for rx, ry in nose[1]
            )
            if not common_tip or not fins[0] or not fins[1]:
                continue
            left = min(fins[0], key=lambda edge: edge[0][1])
            right = min(fins[1], key=lambda edge: edge[0][1])
            candidates.append(RocketGeometry((x1, y1, x2, y2), left, right))
    # Multiple possible vehicles or ambiguous structures are not silently selected.
    return candidates[0] if len(candidates) == 1 else None
