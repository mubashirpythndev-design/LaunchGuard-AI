"""Agent tool wrappers for computer vision execution (T065, Constitution 2.I, 3.III).

Provides typed, pure tool functions returning list[Finding]:
- inspect_body
- check_fin_alignment
- check_launchpad_clear
"""

from __future__ import annotations

import cv2
import numpy as np

from cv.body import inspect_body as _cv_inspect_body
from cv.cues import (
    detect_flame as _cv_detect_flame,
)
from cv.cues import (
    detect_leak as _cv_detect_leak,
)
from cv.cues import (
    detect_motion as _cv_detect_motion,
)
from cv.cues import (
    detect_smoke as _cv_detect_smoke,
)
from cv.failsafe import failsafe
from cv.fins import check_fin_alignment as _cv_check_fin_alignment
from cv.models import predict_objects
from cv.reference import ReferenceAnalysis
from cv.reference import analyze_reference as _cv_analyze_reference
from cv.reference import compare_reference as _cv_compare_reference
from rule_engine.config import MIN_CONFIDENCE_FOR_OK
from rule_engine.escalation import apply_cue_escalation
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Quadrant,
    Severity,
    Thresholds,
)


def compare_reference(
    reference_img: np.ndarray, current_img: np.ndarray, quadrant: Quadrant
) -> Finding:
    """Compare a current quadrant with its stored golden reference."""
    return _cv_compare_reference(reference_img, current_img, quadrant)


def compare_reference_evidence(
    reference_img: np.ndarray, current_img: np.ndarray, quadrant: Quadrant
) -> ReferenceAnalysis:
    """Compare a quadrant and retain server-renderable aligned evidence."""
    return _cv_analyze_reference(reference_img, current_img, quadrant)


def inspect_body(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Inspect rocket fuselage for cracks, dents, damage, burn marks, and missing components."""
    return _cv_inspect_body(img, thresholds)


def check_fin_alignment(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Inspect rocket fin alignment and symmetry."""
    return _cv_check_fin_alignment(img, thresholds)


def _bbox_intersects_polygon(
    bbox: tuple[float, float, float, float],
    polygon: list[tuple[float, float]],
) -> tuple[bool, float]:
    """Determine whether normalized bbox [x1, y1, x2, y2] intersects polygon."""
    if len(polygon) < 3:
        return False, 0.0

    bx1, by1, bx2, by2 = bbox
    # Check if any corner of the bbox is inside the polygon
    corners = [(bx1, by1), (bx2, by1), (bx2, by2), (bx1, by2), ((bx1 + bx2) / 2, (by1 + by2) / 2)]

    poly_pts = np.array(
        [[int(round(p[0] * 1000)), int(round(p[1] * 1000))] for p in polygon],
        dtype=np.int32,
    )

    inside_count = 0
    for cx, cy in corners:
        pt = (int(round(cx * 1000)), int(round(cy * 1000)))
        dist = cv2.pointPolygonTest(poly_pts, pt, measureDist=False)
        if dist >= 0:
            inside_count += 1

    overlap_ratio = float(inside_count) / float(len(corners))
    return inside_count > 0, overlap_ratio


@failsafe(
    module="cv.pad",
    name="Launchpad clearance check",
    check_id="zone.occupancy",
    step_position=3,
)
def check_launchpad_clear(
    img: np.ndarray,
    danger_zone: list[tuple[float, float]] | None = None,
    thresholds: Thresholds | None = None,
) -> list[Finding]:
    """Detect people and foreign objects in or near the launchpad danger zone."""
    cfg = thresholds or Thresholds()
    # Class 0 in COCO is person
    detections = predict_objects(img, conf=cfg.detector_conf, iou=cfg.detector_iou, classes=[0])

    if not danger_zone or len(danger_zone) < 3:
        if detections:
            top_det = max(detections, key=lambda d: d.confidence)
            count_m = Measurement(name="person_count", value=float(len(detections)), unit="count")
            return [
                Finding(
                    module="cv.pad",
                    check_id="zone.occupancy",
                    severity=Severity.WARNING,
                    message="Personnel detected on launchpad; danger zone not formally designated.",
                    confidence=round(top_det.confidence, 2),
                    metrics=(count_m,),
                    overlay=Overlay(
                        kind=OverlayKind.BBOX,
                        check_id="zone.occupancy",
                        points=(
                            (top_det.bbox_norm[0], top_det.bbox_norm[1]),
                            (top_det.bbox_norm[2], top_det.bbox_norm[3]),
                        ),
                        label="Person",
                    ),
                    step_position=3,
                )
            ]
        return [
            Finding(
                module="cv.pad",
                check_id="zone.occupancy",
                severity=Severity.OK,
                message="Launchpad area clear of personnel; no danger exclusion zone marked.",
                confidence=MIN_CONFIDENCE_FOR_OK,
                metrics=(Measurement(name="person_count", value=0.0, unit="count"),),
                overlay=None,
                step_position=3,
            )
        ]

    # Evaluate overlap with marked danger zone
    person_in_zone = False
    max_overlap = 0.0
    violating_det = None

    for det in detections:
        intersects, ratio = _bbox_intersects_polygon(det.bbox_norm, danger_zone)
        if intersects:
            person_in_zone = True
            if ratio >= max_overlap:
                max_overlap = ratio
                violating_det = det

    if person_in_zone and violating_det is not None:
        return [
            Finding(
                module="cv.pad",
                check_id="zone.occupancy",
                severity=cfg.object_in_zone_severity,
                message="A person appears to be inside the marked danger zone.",
                confidence=round(violating_det.confidence, 2),
                metrics=(
                    Measurement(
                        name="overlap_ratio",
                        value=round(max_overlap, 2),
                        unit="ratio",
                        threshold=0.0,
                    ),
                ),
                overlay=Overlay(
                    kind=OverlayKind.BBOX,
                    check_id="zone.occupancy",
                    points=(
                        (violating_det.bbox_norm[0], violating_det.bbox_norm[1]),
                        (violating_det.bbox_norm[2], violating_det.bbox_norm[3]),
                    ),
                    label="Person in Zone",
                ),
                step_position=3,
            )
        ]

    return [
        Finding(
            module="cv.pad",
            check_id="zone.occupancy",
            severity=Severity.OK,
            message="Marked danger zone is clear of personnel.",
            confidence=0.90,
            metrics=(Measurement(name="overlap_ratio", value=0.0, unit="ratio", threshold=0.0),),
            overlay=None,
            step_position=3,
        )
    ]


def detect_flame(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Detect flame or thermal ignition cues in the launchpad area (cue.fire)."""
    return _cv_detect_flame(img, thresholds)


def detect_smoke(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Detect smoke plume or vapor cloud dispersion in launchpad area (cue.smoke)."""
    return _cv_detect_smoke(img, thresholds)


def detect_leak(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Detect liquid pooling or propellant leak near vehicle base (cue.leak)."""
    return _cv_detect_leak(img, thresholds)


def detect_motion(
    img: np.ndarray,
    reference_img: np.ndarray | None = None,
    thresholds: Thresholds | None = None,
) -> list[Finding]:
    """Detect unexpected base motion or structural displacement (cue.motion)."""
    return _cv_detect_motion(img, reference_img, thresholds)


def check_launchpad_cues(
    img: np.ndarray,
    reference_img: np.ndarray | None = None,
    thresholds: Thresholds | None = None,
) -> list[Finding]:
    """Execute all four cue detectors and apply safety escalation rules."""
    findings: list[Finding] = []
    findings.extend(_cv_detect_flame(img, thresholds))
    findings.extend(_cv_detect_smoke(img, thresholds))
    findings.extend(_cv_detect_leak(img, thresholds))
    findings.extend(_cv_detect_motion(img, reference_img, thresholds))
    return apply_cue_escalation(findings)
