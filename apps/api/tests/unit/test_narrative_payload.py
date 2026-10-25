"""Unit test for narrative payload no-image-bytes guarantee (T099, FR-039, SH-009).

Asserts that the serialized narrative payload:
- Contains no data URIs (data:image)
- Contains no base64-encoded strings
- Contains no image MIME types (image/jpeg, image/png, image/webp)
- Contains no absolute filesystem paths
- Contains no run-local image references (.jpg, .png, .webp)
"""

from __future__ import annotations

import re

import pytest

from agent.narrative import (
    build_narrative_context,
    serialize_narrative_payload,
    validate_payload_safety,
)
from rule_engine.types import (
    Finding,
    Measurement,
    Overlay,
    OverlayKind,
    Severity,
    Verdict,
)


def test_narrative_payload_excludes_all_image_data_and_paths() -> None:
    """Verify serialized narrative payload contains zero image bytes, MIME types, or paths."""
    # Finding with an overlay that should be stripped by build_narrative_context
    finding = Finding(
        module="cv.fins",
        check_id="fin.alignment",
        severity=Severity.WARNING,
        message=(
            "Fin angle deviation appears to be 4.2°, which may exceed the 3.0° warning threshold."
        ),
        confidence=0.81,
        metrics=(
            Measurement(
                name="fin_angle_deviation",
                value=4.2,
                unit="deg",
                error_margin=1.5,
                threshold=3.0,
            ),
        ),
        overlay=Overlay(
            kind=OverlayKind.ARC,
            check_id="fin.alignment",
            points=((0.2, 0.3), (0.4, 0.5)),
            label="4.2° deviation",
        ),
        step_position=2,
        near_threshold_note="Measured 4.2° ± 1.5°; warning threshold is 3.0°",
    )

    reasons = [
        {
            "check_id": "fin.alignment",
            "severity": "warning",
            "message": "Fin angle deviation appears to be 4.2°",
            "confidence": 0.81,
            "ambiguous": True,
        }
    ]

    context = build_narrative_context(
        verdict=Verdict.HOLD,
        risk_score=52,
        reasons=reasons,
        findings=[finding],
    )

    payload_json = serialize_narrative_payload(context)

    # 1. Assert denylist strings are absent
    prohibited_substrings = [
        "data:image",
        "base64",
        "image/jpeg",
        "image/png",
        "image/webp",
        ".jpg",
        ".png",
        ".webp",
        "media/runs",
    ]
    for prohibited in prohibited_substrings:
        assert prohibited not in payload_json.lower(), f"Prohibited string '{prohibited}' leaked!"

    # 2. Assert no absolute paths (Windows C:\ or Unix /home/, /tmp/)
    assert not re.search(r"[a-zA-Z]:[\\/]", payload_json), (
        "Absolute Windows filesystem path leaked!"
    )
    assert not re.search(r"/(?:home|tmp|var|usr)/", payload_json), "Absolute Unix path leaked!"

    # 3. Assert no overlay points leaked
    assert "0.2" not in payload_json
    assert "0.4" not in payload_json
    assert "points" not in payload_json

    # 4. Built-in validator passes cleanly
    validate_payload_safety(payload_json)


def test_narrative_payload_validation_rejects_leakage() -> None:
    """Verify validate_payload_safety raises ValueError on prohibited content."""
    with pytest.raises(ValueError, match="Prohibited substring 'base64'"):
        validate_payload_safety('{"data": "base64,deadbeef"}')

    with pytest.raises(ValueError, match="Prohibited substring 'data:image'"):
        validate_payload_safety('{"preview": "data:image/png;base64,abc"}')

    with pytest.raises(ValueError, match="Absolute Windows path"):
        validate_payload_safety('{"path": "D:\\\\Works\\\\images\\\\sample_folder"}')
