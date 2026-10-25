"""Banded saturating risk score computation (Plan R7, Constitution 2.I).

Risk score is advisory (0–100), strictly order-independent, and NEVER an input to the verdict.
Bands:
  GO    -> 0–30
  HOLD  -> 40–69
  NO-GO -> 70–100
"""

from __future__ import annotations

from collections.abc import Sequence

from rule_engine.config import CRITICAL_CAPACITY, MIN_CONFIDENCE_FOR_OK, WARNING_CAPACITY
from rule_engine.types import Finding, Severity, Verdict


def compute_risk_score(findings: Sequence[Finding], verdict: Verdict) -> int:
    """Compute verdict-banded saturating risk score."""
    warning_evidence = sum(0.25 * f.confidence for f in findings if f.severity == Severity.WARNING)
    critical_evidence = sum(
        1.00 * f.confidence for f in findings if f.severity == Severity.CRITICAL
    )
    low_confidence = sum(
        (MIN_CONFIDENCE_FOR_OK - f.confidence)
        for f in findings
        if f.severity == Severity.OK and 0 < f.confidence < MIN_CONFIDENCE_FOR_OK
    )

    if verdict == Verdict.GO:
        score = round(100.0 * min(0.30, low_confidence / 0.60))
        return max(0, min(30, score))
    elif verdict == Verdict.HOLD:
        score = round(40.0 + 29.0 * min(1.0, warning_evidence / WARNING_CAPACITY))
        return max(40, min(69, score))
    else:  # NO_GO
        score = round(70.0 + 30.0 * min(1.0, critical_evidence / CRITICAL_CAPACITY))
        return max(70, min(100, score))


def risk_band(score: int) -> str:
    """Return qualitative risk band label."""
    if score <= 30:
        return "low"
    elif score <= 69:
        return "elevated"
    return "severe"
