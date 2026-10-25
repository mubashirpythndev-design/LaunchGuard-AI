"""Launchpad hazard cues detection module (T095, US3, FR-015, Constitution 2.I, 3.III).

Pure functions analyzing launchpad imagery for smoke, flame, liquid pooling, and abnormal motion.
All findings map to the shared launchpad_area checklist step (position 3).
"""

from __future__ import annotations

import cv2
import numpy as np

from cv.failsafe import failsafe
from cv.frameio import assess_frame_quality
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Thresholds,
)


@failsafe(module="cv.cues", name="Flame detection", check_id="cue.fire", step_position=3)
def detect_flame(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Detect active flame, fire, or thermal ignition cues in the launchpad area."""
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.fire",
                severity=Severity.WARNING,
                message="Zero-dimension frame provided for flame detection.",
                confidence=0.0,
                metrics=(Measurement(name="frame_size", value=0.0, unit="px"),),
                step_position=3,
                degraded=True,
            )
        ]

    # Check frame illumination and quality
    is_nominal, quality_conf, quality_msg = assess_frame_quality(img)
    if not is_nominal:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.fire",
                severity=Severity.WARNING,
                message=f"Low illumination or contrast for flame detection ({quality_msg}).",
                confidence=quality_conf,
                metrics=(
                    Measurement(
                        name="flame_coverage_ratio", value=0.0, unit="ratio", threshold=0.0005
                    ),
                ),
                step_position=3,
                degraded=True,
                near_threshold_note=quality_msg,
            )
        ]

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Segment high-intensity flame colors: red, orange, and bright yellow in HSV
    lower_fire1 = np.array([0, 110, 180], dtype=np.uint8)
    upper_fire1 = np.array([35, 255, 255], dtype=np.uint8)
    lower_fire2 = np.array([170, 110, 180], dtype=np.uint8)
    upper_fire2 = np.array([180, 255, 255], dtype=np.uint8)

    mask1 = cv2.inRange(hsv, lower_fire1, upper_fire1)
    mask2 = cv2.inRange(hsv, lower_fire2, upper_fire2)
    flame_mask = cv2.bitwise_or(mask1, mask2)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    flame_mask = cv2.morphologyEx(flame_mask, cv2.MORPH_OPEN, kernel)

    flame_pixels = int(cv2.countNonZero(flame_mask))
    coverage = float(flame_pixels) / float(h * w)

    threshold = 0.0005  # 0.05% of frame

    if coverage >= threshold:
        pts = np.argwhere(flame_mask > 0)
        y_min, x_min = pts.min(axis=0)
        y_max, x_max = pts.max(axis=0)

        norm_x1 = max(0.0, min(1.0, float(x_min) / float(w)))
        norm_y1 = max(0.0, min(1.0, float(y_min) / float(h)))
        norm_x2 = max(0.0, min(1.0, float(x_max) / float(w)))
        norm_y2 = max(0.0, min(1.0, float(y_max) / float(h)))

        conf = min(0.95, round(0.75 + coverage * 20.0, 2))
        return [
            Finding(
                module="cv.cues",
                check_id="cue.fire",
                severity=Severity.CRITICAL,
                message="Visual evidence consistent with active flame detected near pad area.",
                confidence=conf,
                metrics=(
                    Measurement(
                        name="flame_coverage_ratio",
                        value=round(coverage, 4),
                        unit="ratio",
                        threshold=threshold,
                    ),
                ),
                overlay=Overlay(
                    kind=OverlayKind.BBOX,
                    check_id="cue.fire",
                    points=((norm_x1, norm_y1), (norm_x2, norm_y2)),
                    label="Flame Indication",
                ),
                step_position=3,
            )
        ]

    pad_overlay = Overlay(
        kind=OverlayKind.BBOX,
        check_id="cue.fire",
        points=((0.0, 0.25), (1.0, 1.0)),
        label="Launchpad Area",
    )

    return [
        Finding(
            module="cv.cues",
            check_id="cue.fire",
            severity=Severity.OK,
            message="No flame or fire indications detected in pad area.",
            confidence=0.92,
            metrics=(
                Measurement(
                    name="flame_coverage_ratio",
                    value=0.0,
                    unit="ratio",
                    threshold=threshold,
                ),
            ),
            overlay=pad_overlay,
            step_position=3,
        )
    ]


@failsafe(module="cv.cues", name="Smoke detection", check_id="cue.smoke", step_position=3)
def detect_smoke(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Detect smoke plumes, heavy aerosol dispersion, or abnormal vapor clouds."""
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.smoke",
                severity=Severity.WARNING,
                message="Zero-dimension frame provided for smoke detection.",
                confidence=0.0,
                metrics=(Measurement(name="frame_size", value=0.0, unit="px"),),
                step_position=3,
                degraded=True,
            )
        ]

    is_nominal, quality_conf, quality_msg = assess_frame_quality(img)
    if not is_nominal:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.smoke",
                severity=Severity.WARNING,
                message=f"Low illumination or contrast for smoke detection ({quality_msg}).",
                confidence=quality_conf,
                metrics=(
                    Measurement(
                        name="smoke_coverage_ratio", value=0.0, unit="ratio", threshold=0.01
                    ),
                ),
                step_position=3,
                degraded=True,
                near_threshold_note=quality_msg,
            )
        ]

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Smoke segmentation: low saturation (gray/whitish) with mid-to-high luminance
    lower_smoke = np.array([0, 0, 120], dtype=np.uint8)
    upper_smoke = np.array([180, 40, 220], dtype=np.uint8)
    smoke_mask = cv2.inRange(hsv, lower_smoke, upper_smoke)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    smoke_mask = cv2.morphologyEx(smoke_mask, cv2.MORPH_OPEN, kernel)

    smoke_pixels = int(cv2.countNonZero(smoke_mask))
    coverage = float(smoke_pixels) / float(h * w)

    threshold = 0.02  # 2% of frame for significant smoke plume diffusion

    if coverage >= threshold:
        pts = np.argwhere(smoke_mask > 0)
        y_min, x_min = pts.min(axis=0)
        y_max, x_max = pts.max(axis=0)

        norm_x1 = max(0.0, min(1.0, float(x_min) / float(w)))
        norm_y1 = max(0.0, min(1.0, float(y_min) / float(h)))
        norm_x2 = max(0.0, min(1.0, float(x_max) / float(w)))
        norm_y2 = max(0.0, min(1.0, float(y_max) / float(h)))

        return [
            Finding(
                module="cv.cues",
                check_id="cue.smoke",
                severity=Severity.WARNING,
                message="Visual evidence consistent with smoke plume or vapor cloud detected.",
                confidence=0.86,
                metrics=(
                    Measurement(
                        name="smoke_coverage_ratio",
                        value=round(coverage, 4),
                        unit="ratio",
                        threshold=threshold,
                    ),
                ),
                overlay=Overlay(
                    kind=OverlayKind.BBOX,
                    check_id="cue.smoke",
                    points=((norm_x1, norm_y1), (norm_x2, norm_y2)),
                    label="Smoke Plume",
                ),
                step_position=3,
            )
        ]

    pad_overlay = Overlay(
        kind=OverlayKind.BBOX,
        check_id="cue.smoke",
        points=((0.0, 0.25), (1.0, 1.0)),
        label="Launchpad Area",
    )

    return [
        Finding(
            module="cv.cues",
            check_id="cue.smoke",
            severity=Severity.OK,
            message="No smoke plumes or abnormal vapor detected.",
            confidence=0.90,
            metrics=(
                Measurement(
                    name="smoke_coverage_ratio",
                    value=0.0,
                    unit="ratio",
                    threshold=threshold,
                ),
            ),
            overlay=pad_overlay,
            step_position=3,
        )
    ]


@failsafe(module="cv.cues", name="Liquid pooling detection", check_id="cue.leak", step_position=3)
def detect_leak(img: np.ndarray, thresholds: Thresholds | None = None) -> list[Finding]:
    """Detect liquid pooling, propellant spills, or wet specular puddles near the vehicle base."""
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.leak",
                severity=Severity.WARNING,
                message="Zero-dimension frame provided for leak detection.",
                confidence=0.0,
                metrics=(Measurement(name="frame_size", value=0.0, unit="px"),),
                step_position=3,
                degraded=True,
            )
        ]

    is_nominal, quality_conf, quality_msg = assess_frame_quality(img)
    if not is_nominal:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.leak",
                severity=Severity.WARNING,
                message=f"Low illumination or contrast for leak detection ({quality_msg}).",
                confidence=quality_conf,
                metrics=(
                    Measurement(name="liquid_pool_area", value=0.0, unit="ratio", threshold=0.001),
                ),
                step_position=3,
                degraded=True,
                near_threshold_note=quality_msg,
            )
        ]

    # Focus inspection on pad floor / base region (bottom 60% of frame)
    deck_y1 = int(0.40 * h)
    deck_crop = img[deck_y1:, :]
    gray_deck = cv2.cvtColor(deck_crop, cv2.COLOR_BGR2GRAY)

    # Detect dark, reflective pooling patches on the pad deck
    pool_mask = cv2.inRange(gray_deck, 5, 38)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    pool_mask = cv2.morphologyEx(pool_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(pool_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_contour_area = 0.003 * float(h * w)
    significant_contours = [c for c in contours if cv2.contourArea(c) >= min_contour_area]

    threshold = 0.015

    if significant_contours:
        all_pts = np.vstack(significant_contours)
        x_min, y_min, rw, rh = cv2.boundingRect(all_pts)
        total_pool_area = sum(cv2.contourArea(c) for c in significant_contours)
        pool_ratio = float(total_pool_area) / float(h * w)

        norm_x1 = max(0.0, min(1.0, float(x_min) / float(w)))
        norm_y1 = max(0.0, min(1.0, float(deck_y1 + y_min) / float(h)))
        norm_x2 = max(0.0, min(1.0, float(x_min + rw) / float(w)))
        norm_y2 = max(0.0, min(1.0, float(deck_y1 + y_min + rh) / float(h)))

        return [
            Finding(
                module="cv.cues",
                check_id="cue.leak",
                severity=Severity.WARNING,
                message="Visual evidence consistent with liquid pooling detected near pad base.",
                confidence=0.85,
                metrics=(
                    Measurement(
                        name="liquid_pool_area",
                        value=round(pool_ratio, 4),
                        unit="ratio",
                        threshold=threshold,
                    ),
                ),
                overlay=Overlay(
                    kind=OverlayKind.BBOX,
                    check_id="cue.leak",
                    points=((norm_x1, norm_y1), (norm_x2, norm_y2)),
                    label="Liquid Pooling",
                ),
                step_position=3,
            )
        ]

    pad_overlay = Overlay(
        kind=OverlayKind.BBOX,
        check_id="cue.leak",
        points=((0.0, 0.40), (1.0, 1.0)),
        label="Pad Deck",
    )

    return [
        Finding(
            module="cv.cues",
            check_id="cue.leak",
            severity=Severity.OK,
            message="No liquid pooling or surface leaks detected on pad surface.",
            confidence=0.90,
            metrics=(
                Measurement(
                    name="liquid_pool_area",
                    value=0.0,
                    unit="ratio",
                    threshold=threshold,
                ),
            ),
            overlay=pad_overlay,
            step_position=3,
        )
    ]


@failsafe(
    module="cv.cues", name="Abnormal motion detection", check_id="cue.motion", step_position=3
)
def detect_motion(
    img: np.ndarray,
    reference_img: np.ndarray | None = None,
    thresholds: Thresholds | None = None,
) -> list[Finding]:
    """Detect unexpected movement or displacement in pad area between consecutive frames."""
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.motion",
                severity=Severity.WARNING,
                message="Zero-dimension frame provided for motion detection.",
                confidence=0.0,
                metrics=(Measurement(name="frame_size", value=0.0, unit="px"),),
                step_position=3,
                degraded=True,
            )
        ]

    is_nominal, quality_conf, quality_msg = assess_frame_quality(img)
    if not is_nominal:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.motion",
                severity=Severity.WARNING,
                message=f"Low illumination or contrast for motion detection ({quality_msg}).",
                confidence=quality_conf,
                metrics=(
                    Measurement(
                        name="motion_pixel_ratio", value=0.0, unit="ratio", threshold=0.005
                    ),
                ),
                step_position=3,
                degraded=True,
                near_threshold_note=quality_msg,
            )
        ]

    threshold = 0.005  # 0.5% of frame pixels changing

    pad_overlay = Overlay(
        kind=OverlayKind.BBOX,
        check_id="cue.motion",
        points=((0.0, 0.30), (1.0, 1.0)),
        label="Launchpad Base",
    )

    if reference_img is None:
        return [
            Finding(
                module="cv.cues",
                check_id="cue.motion",
                severity=Severity.OK,
                message="Motion analysis requires sequential frames; single static frame nominal.",
                confidence=0.90,
                metrics=(
                    Measurement(
                        name="motion_pixel_ratio",
                        value=0.0,
                        unit="ratio",
                        threshold=threshold,
                    ),
                ),
                overlay=pad_overlay,
                step_position=3,
            )
        ]

    ref_h, ref_w = reference_img.shape[:2]
    if ref_h != h or ref_w != w:
        ref_resized = cv2.resize(reference_img, (w, h), interpolation=cv2.INTER_AREA)
    else:
        ref_resized = reference_img

    gray_ref = cv2.GaussianBlur(cv2.cvtColor(ref_resized, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    gray_cur = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)

    diff = cv2.absdiff(gray_ref, gray_cur)
    _, thresh = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    motion_pixels = int(cv2.countNonZero(thresh))
    motion_ratio = float(motion_pixels) / float(h * w)

    if motion_ratio >= threshold:
        pts = np.argwhere(thresh > 0)
        y_min, x_min = pts.min(axis=0)
        y_max, x_max = pts.max(axis=0)

        norm_x1 = max(0.0, min(1.0, float(x_min) / float(w)))
        norm_y1 = max(0.0, min(1.0, float(y_min) / float(h)))
        norm_x2 = max(0.0, min(1.0, float(x_max) / float(w)))
        norm_y2 = max(0.0, min(1.0, float(y_max) / float(h)))

        conf = min(0.95, round(0.75 + motion_ratio * 10.0, 2))
        return [
            Finding(
                module="cv.cues",
                check_id="cue.motion",
                severity=Severity.WARNING,
                message="Unexpected movement or displacement detected in vehicle base area.",
                confidence=conf,
                metrics=(
                    Measurement(
                        name="motion_pixel_ratio",
                        value=round(motion_ratio, 4),
                        unit="ratio",
                        threshold=threshold,
                    ),
                ),
                overlay=Overlay(
                    kind=OverlayKind.BBOX,
                    check_id="cue.motion",
                    points=((norm_x1, norm_y1), (norm_x2, norm_y2)),
                    label="Abnormal Motion",
                ),
                step_position=3,
            )
        ]

    return [
        Finding(
            module="cv.cues",
            check_id="cue.motion",
            severity=Severity.OK,
            message="No abnormal motion detected in vehicle base area.",
            confidence=0.90,
            metrics=(
                Measurement(
                    name="motion_pixel_ratio",
                    value=0.0,
                    unit="ratio",
                    threshold=threshold,
                ),
            ),
            overlay=pad_overlay,
            step_position=3,
        )
    ]


def detect_cues(
    img: np.ndarray,
    reference_img: np.ndarray | None = None,
    thresholds: Thresholds | None = None,
) -> list[Finding]:
    """Execute all four launchpad cue detection modules in sequence."""
    findings: list[Finding] = []
    findings.extend(detect_flame(img, thresholds))
    findings.extend(detect_smoke(img, thresholds))
    findings.extend(detect_leak(img, thresholds))
    findings.extend(detect_motion(img, reference_img, thresholds))
    return findings
