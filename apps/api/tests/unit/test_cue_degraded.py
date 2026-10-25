"""Degraded cue detection unit tests (T098, US3, FR-008, Constitution 2.II, 3.III).

Verifies that a uniform or too-dark frame yields low confidence (< MIN_CONFIDENCE_FOR_OK)
from all cue detectors and a 'warning' status rather than an unverified 'ok' result.
"""

from __future__ import annotations

import numpy as np

from cv.cues import (
    detect_cues,
    detect_flame,
    detect_leak,
    detect_motion,
    detect_smoke,
)
from rule_engine.config import MIN_CONFIDENCE_FOR_OK
from rule_engine.types import (
    Severity,
    Verdict,
    validate_finding,
)
from rule_engine.verdict import make_decision


def test_too_dark_frame_yields_warning_and_low_confidence() -> None:
    """A pitch black or near-zero illumination frame yields degraded warning findings."""
    dark_img = np.full((360, 640, 3), 4, dtype=np.uint8)

    detectors = [detect_flame, detect_smoke, detect_leak, detect_motion]
    for det in detectors:
        findings = det(dark_img)
        assert len(findings) == 1
        f = findings[0]
        validate_finding(f)

        assert f.severity == Severity.WARNING
        assert f.degraded is True
        assert f.confidence < MIN_CONFIDENCE_FOR_OK
        assert f.step_position == 3
        assert "illumination" in f.message.lower() or "insufficient" in f.message.lower()

    # Confirm rule engine decision on dark frame is HOLD, never GO
    all_findings = detect_cues(dark_img)
    decision = make_decision(all_findings)
    assert decision.verdict == Verdict.HOLD


def test_uniform_zero_contrast_frame_yields_warning() -> None:
    """A completely uniform frame (zero texture/contrast) yields degraded warning findings."""
    uniform_img = np.full((360, 640, 3), 125, dtype=np.uint8)

    detectors = [detect_flame, detect_smoke, detect_leak, detect_motion]
    for det in detectors:
        findings = det(uniform_img)
        assert len(findings) == 1
        f = findings[0]
        validate_finding(f)

        assert f.severity == Severity.WARNING
        assert f.degraded is True
        assert f.confidence < MIN_CONFIDENCE_FOR_OK
        assert f.step_position == 3
        assert "contrast" in f.message.lower() or "uniform" in f.message.lower()

    all_findings = detect_cues(uniform_img)
    decision = make_decision(all_findings)
    assert decision.verdict == Verdict.HOLD
