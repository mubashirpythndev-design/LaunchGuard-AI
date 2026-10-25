"""Fin symmetry and alignment inspection module (T062, FR-011, FR-043, SC-002).

Computes fin angle deviation with declared error_margin=1.5 deg, producing an ARC
overlay and flagging boundary ambiguity when measurement sits within error margin of threshold.
"""

from __future__ import annotations

import numpy as np

from cv.failsafe import failsafe
from cv.frameio import assess_frame_quality
from cv.subject import locate_rocket, unavailable
from rule_engine.config import apply_confidence_floor
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Thresholds,
    is_threshold_ambiguous,
)


def evaluate_fin_deviation(
    deviation_deg: float,
    thresholds: Thresholds | None = None,
    overlay: Overlay | None = None,
    base_confidence: float = 0.90,
) -> Finding:
    """Evaluate a numeric fin angle deviation against thresholds.

    Boundary rule (FR-011): strictly greater-than. Exactly 3.0 deg and 6.0 deg
    fall on less-severe side.
    Ambiguity (FR-043, SH-007): within error_margin of threshold carries near_threshold_note.
    """
    cfg = thresholds or Thresholds()
    warn_thresh = cfg.fin_angle_warning_deg
    crit_thresh = cfg.fin_angle_critical_deg
    error_margin = cfg.fin_angle_error_margin_deg

    if deviation_deg > crit_thresh:
        sev = Severity.CRITICAL
        msg = (
            f"Fin angle deviation {deviation_deg:.1f} deg exceeds critical threshold "
            f"({crit_thresh:.1f} deg). Possible fin asymmetry; manual verification required."
        )
    elif deviation_deg > warn_thresh:
        sev = Severity.WARNING
        msg = (
            f"Fin angle deviation {deviation_deg:.1f} deg exceeds warning threshold "
            f"({warn_thresh:.1f} deg). Manual fin trim inspection recommended."
        )
    else:
        sev = Severity.OK
        msg = (
            f"Fin alignment within tolerance (deviation {deviation_deg:.1f} deg, "
            f"threshold {warn_thresh:.1f} deg)."
        )

    # Associate measurement with the nearest decision threshold to evaluate boundary ambiguity
    dist_warn = abs(deviation_deg - warn_thresh)
    dist_crit = abs(deviation_deg - crit_thresh)
    active_thresh = crit_thresh if dist_crit < dist_warn else warn_thresh

    dev_measurement = Measurement(
        name="fin_angle_deviation",
        value=round(deviation_deg, 2),
        unit="deg",
        error_margin=error_margin,
        threshold=active_thresh,
    )

    near_note: str | None = None
    if is_threshold_ambiguous(dev_measurement):
        near_note = (
            f"Measurement {deviation_deg:.1f} deg is within ±{error_margin:.1f} deg error margin "
            f"of threshold ({active_thresh:.1f} deg); outcome is not definitively distinguishable."
        )

    return apply_confidence_floor(Finding(
        module="cv.fins",
        check_id="fin.alignment",
        severity=sev,
        message=msg,
        confidence=round(base_confidence, 2),
        metrics=(dev_measurement,),
        overlay=overlay,
        step_position=2,
        near_threshold_note=near_note,
    ))


@failsafe(module="cv.fins", name="Fin alignment", check_id="fin.alignment", step_position=2)
def check_fin_alignment(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Inspect fin symmetry and alignment from rocket frame.

    Pure function returning a list with a single fin.alignment finding.
    """
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return [
            Finding(
                module="cv.fins",
                check_id="fin.alignment",
                severity=Severity.WARNING,
                message="Zero-dimension frame provided for fin inspection.",
                confidence=0.0,
                metrics=(Measurement(name="frame_size", value=0.0, unit="px"),),
                step_position=2,
                degraded=True,
            )
        ]

    is_nominal, quality_conf, quality_msg = assess_frame_quality(img)
    subject = locate_rocket(img)
    if subject is None:
        return [unavailable(
            "cv.fins", "fin.subject_unverified", 2,
            "Rocket body, nose and two measurable fin edges could not be verified.",
        )]
    base_conf = subject.confidence * quality_conf
    x1, y1, x2, y2 = subject.body
    cfg = thresholds or Thresholds()
    # Angles come from measured line segments, not unrelated edge asymmetry.
    angles = []
    for (rx, ry), (tx, ty) in (subject.left_fin, subject.right_fin):
        angles.append(float(np.degrees(np.arctan2(abs(tx - rx), abs(ty - ry)))))
    deviation = abs(angles[0] - angles[1])

    # Center root normalized point for ARC
    norm_cx = round(float((x1 + x2) // 2) / float(w), 3)
    norm_cy = round(float(y2) / float(h), 3)
    arc_overlay = Overlay(
        kind=OverlayKind.ARC,
        check_id="fin.alignment",
        points=((norm_cx, norm_cy),),
        radius=round(float(x2 - x1) / float(w), 3),
        start_deg=0.0,
        end_deg=round(deviation, 1),
        label=f"Fin Deviation {deviation:.1f} deg",
    )

    finding = evaluate_fin_deviation(
        deviation_deg=deviation,
        thresholds=cfg,
        overlay=arc_overlay,
        base_confidence=base_conf,
    )

    return [finding]
