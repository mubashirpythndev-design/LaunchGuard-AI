"""Golden-reference alignment and structural deviation analysis.

All measurements are derived from input pixels. The module is stateless and never
produces a launch verdict; it emits one structured Finding for the rule engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from rule_engine.types import Finding, Measurement, Overlay, OverlayKind, Quadrant, Severity

MIN_GOOD_MATCHES = 10
MAX_ROTATION_DEG = 25.0
WARNING_AREA_PCT = 0.5
CRITICAL_AREA_PCT = 2.0
CRITICAL_EDGE_AREA_PCT = 0.6
MIN_CONTOUR_AREA_PX = 36.0


@dataclass(frozen=True)
class ReferenceAnalysis:
    """Immutable output used to serialize measured evidence and the finding."""

    finding: Finding
    aligned_current: NDArray[np.uint8] | None
    heatmap_bgr: NDArray[np.uint8] | None


def _degraded(quadrant: Quadrant, check_id: str, reason: str) -> ReferenceAnalysis:
    return ReferenceAnalysis(
        finding=Finding(
            module="cv.reference",
            check_id=check_id,
            severity=Severity.WARNING,
            message=f"{quadrant.title()}: Reference comparison unavailable ({reason}); "
            "manual baseline comparison required.",
            confidence=0.0,
            metrics=(Measurement("comparison_available", 0.0, "status"),),
            step_position=1,
            degraded=True,
            quadrant=quadrant,
        ),
        aligned_current=None,
        heatmap_bgr=None,
    )


def _ssim_map(
    reference: NDArray[np.uint8], current: NDArray[np.uint8]
) -> tuple[float, NDArray[np.float32]]:
    """Compute local structural similarity without a browser or external service."""
    ref = reference.astype(np.float32)
    cur = current.astype(np.float32)
    c1 = float((0.01 * 255.0) ** 2)
    c2 = float((0.03 * 255.0) ** 2)
    mu_ref = cv2.GaussianBlur(ref, (11, 11), 1.5)
    mu_cur = cv2.GaussianBlur(cur, (11, 11), 1.5)
    mu_ref_sq = mu_ref * mu_ref
    mu_cur_sq = mu_cur * mu_cur
    mu_cross = mu_ref * mu_cur
    sigma_ref = cv2.GaussianBlur(ref * ref, (11, 11), 1.5) - mu_ref_sq
    sigma_cur = cv2.GaussianBlur(cur * cur, (11, 11), 1.5) - mu_cur_sq
    sigma_cross = cv2.GaussianBlur(ref * cur, (11, 11), 1.5) - mu_cross
    numerator = (2.0 * mu_cross + c1) * (2.0 * sigma_cross + c2)
    denominator = (mu_ref_sq + mu_cur_sq + c1) * (sigma_ref + sigma_cur + c2)
    similarity = np.clip(numerator / np.maximum(denominator, 1e-6), -1.0, 1.0)
    return float(np.mean(similarity)), similarity.astype(np.float32)


def _normalized_polygon(
    contour: NDArray[np.int32], width: int, height: int
) -> tuple[tuple[float, float], ...]:
    epsilon = 0.012 * cv2.arcLength(contour, True)
    points = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
    if len(points) < 3:
        x, y, w, h = cv2.boundingRect(contour)
        points = np.array(((x, y), (x + w, y), (x + w, y + h), (x, y + h)))
    return tuple(
        (max(0.0, min(1.0, float(x) / width)), max(0.0, min(1.0, float(y) / height)))
        for x, y in points
    )


def analyze_reference(
    reference_bgr: NDArray[np.uint8],
    current_bgr: NDArray[np.uint8],
    quadrant: Quadrant,
) -> ReferenceAnalysis:
    """Align current to its golden reference and measure new structural deviation."""
    try:
        if reference_bgr.ndim != 3 or current_bgr.ndim != 3:
            return _degraded(quadrant, "reference.invalid_image", "invalid image shape")
        ref_h, ref_w = reference_bgr.shape[:2]
        cur_h, cur_w = current_bgr.shape[:2]
        if min(ref_h, ref_w, cur_h, cur_w) < 64:
            return _degraded(quadrant, "reference.invalid_image", "image resolution too low")

        ref_gray = cast(NDArray[np.uint8], cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2GRAY))
        cur_gray = cast(NDArray[np.uint8], cv2.cvtColor(current_bgr, cv2.COLOR_BGR2GRAY))
        orb = cv2.ORB_create(nfeatures=2000, fastThreshold=7)  # type: ignore[attr-defined]
        ref_points, ref_desc = orb.detectAndCompute(ref_gray, None)
        cur_points, cur_desc = orb.detectAndCompute(cur_gray, None)
        if ref_desc is None or cur_desc is None:
            return _degraded(quadrant, "reference.alignment_failed", "insufficient visual features")

        pairs = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(cur_desc, ref_desc, k=2)
        good = [first for first, second in pairs if first.distance < 0.75 * second.distance]
        if len(good) < MIN_GOOD_MATCHES:
            return _degraded(
                quadrant, "reference.alignment_failed", f"only {len(good)} reliable feature matches"
            )

        source_values = [
            (float(cur_points[match.queryIdx].pt[0]), float(cur_points[match.queryIdx].pt[1]))
            for match in good
        ]
        target_values = [
            (float(ref_points[match.trainIdx].pt[0]), float(ref_points[match.trainIdx].pt[1]))
            for match in good
        ]
        source = np.asarray(source_values, dtype=np.float32).reshape(-1, 1, 2)
        target = np.asarray(target_values, dtype=np.float32).reshape(-1, 1, 2)
        homography, inlier_mask = cv2.findHomography(source, target, cv2.RANSAC, 4.0)
        if homography is None or inlier_mask is None:
            return _degraded(
                quadrant, "reference.alignment_failed", "homography could not be solved"
            )
        inliers = int(np.count_nonzero(inlier_mask))
        if inliers < MIN_GOOD_MATCHES:
            return _degraded(
                quadrant, "reference.alignment_failed", f"only {inliers} alignment inliers"
            )

        rotation = abs(degrees(atan2(float(homography[1, 0]), float(homography[0, 0]))))
        corner_values: tuple[tuple[float, float], ...] = (
            (0.0, 0.0),
            (float(cur_w), 0.0),
            (float(cur_w), float(cur_h)),
            (0.0, float(cur_h)),
        )
        corners = np.asarray(corner_values, dtype=np.float32).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
        projected_area = abs(float(cv2.contourArea(projected.astype(np.float32))))
        area_ratio = projected_area / float(ref_w * ref_h)
        if rotation > MAX_ROTATION_DEG or not 0.35 <= area_ratio <= 2.5:
            return _degraded(
                quadrant,
                "reference.alignment_failed",
                f"camera perspective outside alignment tolerance ({rotation:.1f} deg)",
            )

        aligned = cast(
            NDArray[np.uint8], cv2.warpPerspective(current_bgr, homography, (ref_w, ref_h))
        )
        valid = cast(
            NDArray[np.uint8],
            cv2.warpPerspective(
                np.full((cur_h, cur_w), 255, dtype=np.uint8), homography, (ref_w, ref_h)
            ),
        )
        # Refine sub-pixel residuals left by discrete ORB keypoints. Failure to refine is
        # harmless because the RANSAC homography has already passed the safety gates.
        aligned_gray = cast(NDArray[np.uint8], cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY))
        fine_warp = np.eye(2, 3, dtype=np.float32)
        try:
            _, fine_result = cv2.findTransformECC(
                ref_gray,
                aligned_gray,
                fine_warp,
                cv2.MOTION_AFFINE,
                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5),
            )
            fine_warp = cast(NDArray[np.float32], fine_result)
            flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
            aligned = cast(
                NDArray[np.uint8],
                cv2.warpAffine(aligned, fine_warp, (ref_w, ref_h), flags=flags),
            )
            valid = cast(
                NDArray[np.uint8],
                cv2.warpAffine(valid, fine_warp, (ref_w, ref_h), flags=flags),
            )
            aligned_gray = cast(
                NDArray[np.uint8], cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
            )
        except cv2.error:
            pass
        valid = cast(
            NDArray[np.uint8],
            # Pixels outside the image are invalid, not OpenCV's default high-valued
            # erosion border. Exclude the SSIM window's radius from every edge.
            cv2.erode(
                valid,
                np.ones((13, 13), dtype=np.uint8),
                iterations=1,
                borderType=cv2.BORDER_CONSTANT,
                borderValue=0,
            ),
        )
        valid_pixels = int(np.count_nonzero(valid))
        if valid_pixels < int(ref_w * ref_h * 0.35):
            return _degraded(
                quadrant, "reference.alignment_failed", "insufficient overlapping surface"
            )

        ssim_score, similarity = _ssim_map(ref_gray, aligned_gray)
        difference = np.clip((1.0 - similarity) * 255.0, 0.0, 255.0).astype(np.uint8)
        difference[valid == 0] = 0
        # A conservative threshold rejects resampling noise after perspective alignment.
        _, anomaly = cv2.threshold(difference, 85, 255, cv2.THRESH_BINARY)
        # Residuals immediately around known edges are usually interpolation from alignment,
        # while a new crack or dent creates pixels beyond the stored edge band.
        reference_edges = cv2.Canny(ref_gray, 80, 180)
        known_edge_band = cv2.dilate(reference_edges, np.ones((15, 15), np.uint8))
        anomaly = cv2.bitwise_and(anomaly, cv2.bitwise_not(known_edge_band))
        anomaly = cv2.morphologyEx(anomaly, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        anomaly = cv2.morphologyEx(anomaly, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))

        contours, _ = cv2.findContours(anomaly, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        kept = [contour for contour in contours if cv2.contourArea(contour) >= MIN_CONTOUR_AREA_PX]
        clean_mask = np.zeros_like(anomaly)
        if kept:
            cv2.drawContours(clean_mask, kept, -1, 255, thickness=cv2.FILLED)
        deviation_area_pct = 100.0 * np.count_nonzero(clean_mask) / valid_pixels

        cur_edges = cv2.Canny(aligned_gray, 80, 180)
        ref_edge_band = cv2.dilate(reference_edges, np.ones((5, 5), np.uint8))
        new_edges = cv2.bitwise_and(cur_edges, cv2.bitwise_not(ref_edge_band))
        new_edges[valid == 0] = 0
        high_gradient_area_pct = 100.0 * np.count_nonzero(new_edges) / valid_pixels

        if (
            deviation_area_pct > CRITICAL_AREA_PCT
            or high_gradient_area_pct > CRITICAL_EDGE_AREA_PCT
        ):
            severity = Severity.CRITICAL
        elif deviation_area_pct >= WARNING_AREA_PCT:
            severity = Severity.WARNING
        else:
            severity = Severity.OK

        confidence = min(0.99, max(0.35, 0.55 + 0.4 * (inliers / len(good))))
        if severity == Severity.OK:
            message = (
                f"{quadrant.title()}: Current surface appears consistent with the golden reference "
                f"({deviation_area_pct:.2f}% changed area)."
            )
        else:
            message = (
                f"{quadrant.title()}: Surface appears to show a possible structural deviation "
                f"against the golden reference ({deviation_area_pct:.2f}% changed area)."
            )

        if kept:
            largest = cast(NDArray[np.int32], max(kept, key=cv2.contourArea))
            points = _normalized_polygon(largest, ref_w, ref_h)
            label = "Possible reference deviation"
        else:
            points = ((0.02, 0.02), (0.98, 0.02), (0.98, 0.98), (0.02, 0.98))
            label = "Aligned comparison region"

        heatmap = cast(NDArray[np.uint8], cv2.applyColorMap(difference, cv2.COLORMAP_INFERNO))
        heatmap[valid == 0] = 0
        return ReferenceAnalysis(
            finding=Finding(
                module="cv.reference",
                check_id="reference.structural_deviation",
                severity=severity,
                message=message,
                confidence=round(confidence, 3),
                metrics=(
                    Measurement(
                        "deviation_area_pct",
                        round(deviation_area_pct, 3),
                        "%",
                        threshold=CRITICAL_AREA_PCT,
                    ),
                    Measurement("ssim_score", round(ssim_score, 4), "score"),
                    Measurement("alignment_inliers", float(inliers), "count"),
                    Measurement(
                        "high_gradient_area_pct",
                        round(high_gradient_area_pct, 3),
                        "%",
                        threshold=CRITICAL_EDGE_AREA_PCT,
                    ),
                ),
                overlay=Overlay(
                    kind=OverlayKind.POLYGON,
                    check_id="reference.structural_deviation",
                    points=points,
                    label=label,
                ),
                step_position=1,
                quadrant=quadrant,
            ),
            aligned_current=aligned,
            heatmap_bgr=heatmap,
        )
    except Exception as exc:
        return _degraded(quadrant, "reference.analysis_failed", type(exc).__name__)


def compare_reference(
    reference_bgr: NDArray[np.uint8],
    current_bgr: NDArray[np.uint8],
    quadrant: Quadrant,
) -> Finding:
    """Pure agent-tool boundary: image pair in, one structured Finding out."""
    return analyze_reference(reference_bgr, current_bgr, quadrant).finding
