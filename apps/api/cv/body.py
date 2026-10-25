"""Limited 2D surface cues on geometrically supported upright rocket-like views.

Pixel edges, texture and darkness are not trained defect classifications. Only
the sampled visible region is assessed, never whole-vehicle parts completeness.
"""

from __future__ import annotations

import cv2
import numpy as np

from cv.failsafe import failsafe
from cv.frameio import assess_frame_quality
from cv.subject import locate_rocket, unavailable
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Thresholds,
)


def _locate_fuselage(img: np.ndarray) -> tuple[int, int, int, int] | None:
    """Return measured walls only; unsupported images have no fuselage ROI."""
    subject = locate_rocket(img)
    return subject.body if subject else None


@failsafe(module="cv.body", name="Rocket body inspection", check_id="body.damage", step_position=1)
def inspect_body(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Measure sampled surface cues after verifying supported rocket-like geometry.

    Pure function: does not mutate inputs or hold request state.
    """
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return [
            Finding(
                module="cv.body",
                check_id="body.damage",
                severity=Severity.WARNING,
                message="Zero-dimension frame provided for body inspection.",
                confidence=0.0,
                metrics=(Measurement(name="frame_size", value=0.0, unit="px"),),
                step_position=1,
                degraded=True,
            )
        ]

    # Assess frame illumination/quality
    is_nominal, quality_conf, quality_msg = assess_frame_quality(img)
    subject = locate_rocket(img)
    if subject is None:
        return [unavailable(
            "cv.body", "body.subject_unverified", 1,
            "Rocket-like geometry could not be verified in this image.",
        )]
    base_conf = subject.confidence * quality_conf
    x1, y1, x2, y2 = subject.body

    # Inset slightly inside fuselage walls to sample pure vehicle skin
    margin_x = max(3, int((x2 - x1) * 0.08))
    skin_x1 = x1 + margin_x
    skin_x2 = x2 - margin_x

    # Inspect lower fuselage section below roll markings (which sit in upper half)
    skin_y1 = y1 + int((y2 - y1) * 0.56)
    skin_y2 = y1 + int((y2 - y1) * 0.94)

    skin_crop = img[skin_y1:skin_y2, skin_x1:skin_x2]
    if skin_crop.size == 0:
        skin_crop = img[y1:y2, x1:x2]

    # Normalized overlay bounding box for fuselage region
    norm_x1 = max(0.0, min(1.0, float(x1) / float(w)))
    norm_y1 = max(0.0, min(1.0, float(y1) / float(h)))
    norm_x2 = max(0.0, min(1.0, float(x2) / float(w)))
    norm_y2 = max(0.0, min(1.0, float(y2) / float(h)))
    fuselage_overlay = Overlay(
        kind=OverlayKind.BBOX,
        check_id="body.damage",
        points=((norm_x1, norm_y1), (norm_x2, norm_y2)),
        label="Rocket Fuselage",
    )

    # 1. Crack / scratch analysis
    gray_skin = cv2.cvtColor(skin_crop, cv2.COLOR_BGR2GRAY)
    crack_edges = cv2.Canny(gray_skin, 30, 100)
    crack_pixel_count = int(np.count_nonzero(crack_edges))
    crack_threshold = 20.0

    if crack_pixel_count > crack_threshold:
        pts = np.argwhere(crack_edges > 0)
        dy1, dx1 = pts.min(axis=0)
        dy2, dx2 = pts.max(axis=0)
        defect_overlay = Overlay(
            kind=OverlayKind.BBOX,
            check_id="body.cracks",
            points=(
                (float(skin_x1 + dx1) / float(w), float(skin_y1 + dy1) / float(h)),
                (float(skin_x1 + dx2) / float(w), float(skin_y1 + dy2) / float(h)),
            ),
            label="Possible surface edge anomaly",
        )
        cracks_finding = Finding(
            module="cv.body",
            check_id="body.cracks",
            severity=Severity.WARNING,
            message="Possible surface edge anomaly in the sampled body region; a seam, marking "
            "or scratch can produce the same signal. Compare with the baseline before diagnosis.",
            confidence=round(min(0.95, base_conf + 0.05), 2),
            metrics=(
                Measurement(
                    name="crack_edge_density",
                    value=float(crack_pixel_count),
                    unit="px",
                    threshold=crack_threshold,
                ),
            ),
            overlay=defect_overlay,
            step_position=1,
        )
    else:
        cracks_finding = Finding(
            module="cv.body",
            check_id="body.cracks",
            severity=Severity.OK,
            message="No above-threshold edge anomaly measured in the sampled body region. "
            "This does not exclude cracks elsewhere or below image resolution.",
            confidence=round(base_conf, 2),
            metrics=(
                Measurement(
                    name="crack_edge_density",
                    value=float(crack_pixel_count),
                    unit="px",
                    threshold=crack_threshold,
                ),
            ),
            overlay=fuselage_overlay,
            step_position=1,
        )

    # 2. Dents / surface depressions
    laplacian = cv2.Laplacian(gray_skin, cv2.CV_64F)
    dent_var = float(np.var(laplacian))
    dent_threshold = 5000.0
    if dent_var > dent_threshold:
        dents_finding = Finding(
            module="cv.body",
            check_id="body.dents",
            severity=Severity.WARNING,
            message="Possible surface texture anomaly; this 2D measurement "
            "cannot establish a dent.",
            confidence=round(base_conf, 2),
            metrics=(
                Measurement(name="surface_gradient_var", value=round(dent_var, 1), unit="var"),
            ),
            overlay=fuselage_overlay,
            step_position=1,
        )
    else:
        dents_finding = Finding(
            module="cv.body",
            check_id="body.dents",
            severity=Severity.OK,
            message="Sampled surface texture is below the anomaly threshold; dent depth "
            "and hidden surfaces were not assessed.",
            confidence=round(base_conf, 2),
            metrics=(
                Measurement(name="surface_gradient_var", value=round(dent_var, 1), unit="var"),
            ),
            overlay=fuselage_overlay,
            step_position=1,
        )

    # 3. Overall surface / paint damage
    if cracks_finding.severity != Severity.OK or dents_finding.severity != Severity.OK:
        damage_finding = Finding(
            module="cv.body",
            check_id="body.damage",
            severity=Severity.WARNING,
            message="Surface anomalies detected on rocket exterior.",
            confidence=round(base_conf, 2),
            metrics=(
                Measurement(
                    name="anomaly_score",
                    value=float(crack_pixel_count),
                    unit="score",
                ),
            ),
            overlay=cracks_finding.overlay or fuselage_overlay,
            step_position=1,
        )
    else:
        damage_finding = Finding(
            module="cv.body",
            check_id="body.damage",
            severity=Severity.OK,
            message="No above-threshold anomaly measured in the sampled surface region; "
            "this is not a whole-vehicle structural clearance.",
            confidence=round(base_conf, 2),
            metrics=(Measurement(name="anomaly_score", value=0.0, unit="score"),),
            overlay=fuselage_overlay,
            step_position=1,
        )

    # 4. Burn marks / thermal discoloration
    hsv_crop = cv2.cvtColor(skin_crop, cv2.COLOR_BGR2HSV)
    v_channel = hsv_crop[:, :, 2]
    dark_mask = v_channel < 40
    burn_pct = float(np.count_nonzero(dark_mask)) / float(max(1, v_channel.size)) * 100.0
    burn_threshold = 3.0
    if burn_pct > burn_threshold:
        burn_finding = Finding(
            module="cv.body",
            check_id="body.burn_marks",
            severity=Severity.WARNING,
            message="Dark pixels measured in the sampled body region; paint, shadows or "
            "possible discoloration require baseline/manual review, not a confirmed burn.",
            confidence=round(base_conf, 2),
            metrics=(
                Measurement(
                    name="thermal_mark_area",
                    value=round(burn_pct, 2),
                    unit="%",
                    threshold=burn_threshold,
                ),
            ),
            overlay=fuselage_overlay,
            step_position=1,
        )
    else:
        burn_finding = Finding(
            module="cv.body",
            check_id="body.burn_marks",
            severity=Severity.OK,
            message="No dark discoloration or burn marks observed on fuselage.",
            confidence=round(base_conf, 2),
            metrics=(
                Measurement(
                    name="thermal_mark_area",
                    value=round(burn_pct, 2),
                    unit="%",
                    threshold=burn_threshold,
                ),
            ),
            overlay=fuselage_overlay,
            step_position=1,
        )

    # Only the coarse geometry actually observed by the subject gate is reported.
    missing_finding = Finding(
        module="cv.body",
        check_id="body.visible_geometry",
        severity=Severity.OK,
        message="Nose, paired body walls and two fin edges appear visible. "
        "Individual fittings and completeness against an engineering inventory were not assessed.",
        confidence=round(base_conf, 2),
        metrics=(Measurement(name="observed_geometry_groups", value=4.0, unit="count"),),
        overlay=fuselage_overlay,
        step_position=1,
    )

    return [cracks_finding, dents_finding, damage_finding, burn_finding, missing_finding]
