"""Configuration constants and fail-safe confidence floor for rule engine."""

from __future__ import annotations

from dataclasses import replace

from rule_engine.types import Finding, Severity, Thresholds

MIN_CONFIDENCE_FOR_OK: float = 0.35
WARNING_CAPACITY: float = 2.0
CRITICAL_CAPACITY: float = 3.0
DEFAULT_THRESHOLDS = Thresholds()


def apply_confidence_floor(finding: Finding) -> Finding:
    """Apply one-way confidence floor (Constitution 2.II, Research R8).

    Any check with confidence below MIN_CONFIDENCE_FOR_OK cannot be recorded as OK.
    Promotes OK to WARNING. Never downgrades WARNING or CRITICAL.
    """
    if finding.severity == Severity.OK and finding.confidence < MIN_CONFIDENCE_FOR_OK:
        msg = (
            f"{finding.message} (confidence {finding.confidence:.2f} below "
            f"{MIN_CONFIDENCE_FOR_OK} floor; fail-safe requires warning)"
        )
        return replace(
            finding,
            severity=Severity.WARNING,
            message=msg,
            degraded=True,
        )
    if finding.confidence < MIN_CONFIDENCE_FOR_OK or finding.degraded:
        return replace(
            finding,
            severity=Severity.WARNING if finding.severity == Severity.OK else finding.severity,
            degraded=True,
        )
    return finding
