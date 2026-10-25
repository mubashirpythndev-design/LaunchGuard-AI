"""Image decode and quality validation utilities (T059, FR-008, Constitution 3.III).

Decodes image bytes and assesses frame quality (uniform, too-dark, too-bright)
without raising, enabling downstream detectors to return low confidence safely.
"""

from __future__ import annotations

import cv2
import numpy as np

MAX_FRAME_SIDE = 1280
MIN_BRIGHTNESS_MEAN = 18.0
MAX_BRIGHTNESS_MEAN = 242.0
MIN_CONTRAST_STD = 8.0


class CorruptImageError(ValueError):
    """Raised when raw bytes cannot be decoded into an OpenCV image matrix."""


def decode_image(data: bytes, max_side: int = MAX_FRAME_SIDE) -> np.ndarray:
    """Decode raw bytes into a BGR numpy ndarray, resizing if dimensions exceed max_side.

    Raises CorruptImageError if the image bytes are empty or unparseable.
    """
    if not data:
        raise CorruptImageError("Zero-byte image payload received")

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise CorruptImageError("Provided bytes could not be decoded as a valid image")

    h, w = img.shape[:2]
    if max(h, w) > max_side:
        scale = max_side / float(max(h, w))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    return img


def assess_frame_quality(img: np.ndarray) -> tuple[bool, float, str | None]:
    """Evaluate frame clarity and illumination.

    Returns:
        (is_nominal, confidence_factor, issue_description)
    """
    if img.size == 0:
        return False, 0.0, "Empty image frame"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_val = float(np.mean(gray))
    std_val = float(np.std(gray))

    if mean_val < MIN_BRIGHTNESS_MEAN:
        msg = f"Frame illumination too low (mean {mean_val:.1f} < {MIN_BRIGHTNESS_MEAN})"
        return False, 0.25, msg
    if mean_val > MAX_BRIGHTNESS_MEAN:
        msg = f"Frame overexposed (mean {mean_val:.1f} > {MAX_BRIGHTNESS_MEAN})"
        return False, 0.25, msg
    if std_val < MIN_CONTRAST_STD:
        msg = f"Frame lacks visual contrast or is uniform (std {std_val:.1f} < {MIN_CONTRAST_STD})"
        return False, 0.20, msg

    return True, 1.0, None
