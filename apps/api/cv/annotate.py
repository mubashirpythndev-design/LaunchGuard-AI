"""Overlay generation and server-side image annotation renderer (T063, FR-010, Constitution 2.I).

Produces normalized Overlay geometry representations (0.0 to 1.0) and renders
high-contrast, color-coded annotated JPEGs for server-side persistence and export.
Strict adherence to Section 2 design rules: technical line drawings, no emojis, standard colors.
"""

from __future__ import annotations

import cv2
import numpy as np

from rule_engine.types import Finding, Overlay, OverlayKind, Severity

# BGR color mapping corresponding to design tokens
SEVERITY_COLORS_BGR = {
    Severity.OK: (80, 160, 60),  # Muted green
    Severity.WARNING: (40, 140, 220),  # Steel amber/orange
    Severity.CRITICAL: (40, 40, 210),  # Desaturated dark red
}
DEFAULT_COLOR_BGR = (180, 180, 180)  # Neutral graphite


def render_annotated_image(
    img: np.ndarray,
    findings: list[Finding],
    jpeg_quality: int = 90,
) -> bytes:
    """Render overlays on top of image frame and encode as JPEG bytes.

    Pure function: operates on a shallow copy of img without mutating inputs.
    """
    canvas = img.copy()
    h, w = canvas.shape[:2]
    if h == 0 or w == 0:
        return b""

    for f in findings:
        if f.overlay is None:
            continue

        overlay: Overlay = f.overlay
        color = SEVERITY_COLORS_BGR.get(f.severity, DEFAULT_COLOR_BGR)

        if overlay.kind == OverlayKind.BBOX and len(overlay.points) >= 2:
            p1, p2 = overlay.points[0], overlay.points[1]
            x1 = int(round(p1[0] * w))
            y1 = int(round(p1[1] * h))
            x2 = int(round(p2[0] * w))
            y2 = int(round(p2[1] * h))

            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
            label = overlay.label or f.check_id
            text = f"{label} ({f.severity.value})"
            cv2.putText(
                canvas,
                text,
                (x1, max(16, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )

        elif overlay.kind == OverlayKind.ARC and len(overlay.points) >= 1:
            cx = int(round(overlay.points[0][0] * w))
            cy = int(round(overlay.points[0][1] * h))
            radius = int(round((overlay.radius or 0.1) * w))
            start_deg = int(overlay.start_deg or 0.0)
            end_deg = int(overlay.end_deg or 45.0)

            cv2.ellipse(
                canvas,
                (cx, cy),
                (radius, radius),
                0,
                start_deg,
                end_deg,
                color,
                2,
                cv2.LINE_AA,
            )
            label = overlay.label or f"Fin dev {end_deg} deg"
            cv2.putText(
                canvas,
                label,
                (cx - 30, cy + 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )

        elif overlay.kind == OverlayKind.POLYGON and len(overlay.points) >= 3:
            pts = np.array(
                [[int(round(p[0] * w)), int(round(p[1] * h))] for p in overlay.points],
                dtype=np.int32,
            )
            cv2.polylines(canvas, [pts], isClosed=True, color=color, thickness=2)
            if overlay.label:
                cv2.putText(
                    canvas,
                    overlay.label,
                    (pts[0][0], max(16, pts[0][1] - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    color,
                    1,
                    cv2.LINE_AA,
                )

        elif overlay.kind == OverlayKind.POLYLINE and len(overlay.points) >= 2:
            pts = np.array(
                [[int(round(p[0] * w)), int(round(p[1] * h))] for p in overlay.points],
                dtype=np.int32,
            )
            cv2.polylines(canvas, [pts], isClosed=False, color=color, thickness=2)

    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(10, min(100, jpeg_quality))]
    success, buffer = cv2.imencode(".jpg", canvas, encode_params)
    if not success:
        return b""

    return bytes(buffer.tobytes())
