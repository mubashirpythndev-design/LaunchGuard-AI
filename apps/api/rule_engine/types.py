"""Domain types for LaunchGuard AI rule engine.

Constitution 2.I & 2.III:
- Frozen domain dataclasses representing the decision model.
- Imports NOTHING from cv or agent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal


class Severity(StrEnum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


class Verdict(StrEnum):
    GO = "GO"
    HOLD = "HOLD"
    NO_GO = "NO-GO"


class OverlayKind(StrEnum):
    BBOX = "bbox"
    POLYLINE = "polyline"
    POLYGON = "polygon"
    ARC = "arc"
    POINT = "point"


@dataclass(frozen=True)
class Measurement:
    name: str
    value: float
    unit: str
    error_margin: float | None = None
    threshold: float | None = None


def is_threshold_ambiguous(m: Measurement) -> bool:
    """Return True if measurement value sits within its error margin of the threshold."""
    if m.threshold is not None and m.error_margin is not None:
        return abs(m.value - m.threshold) <= m.error_margin
    return False


@dataclass(frozen=True)
class Overlay:
    kind: OverlayKind
    check_id: str
    points: tuple[tuple[float, float], ...] = ()
    radius: float | None = None
    start_deg: float | None = None
    end_deg: float | None = None
    label: str | None = None


@dataclass(frozen=True)
class Finding:
    module: str
    check_id: str
    severity: Severity
    message: str
    confidence: float
    metrics: tuple[Measurement, ...] = ()
    overlay: Overlay | None = None
    step_position: int = 0
    degraded: bool = False
    low_confidence_critical: bool = False
    near_threshold_note: str | None = None


class InadmissibleFinding(Exception):
    """Raised when a finding fails Constitution 2.III invariants."""


OVERLAY_EXEMPT_CHECKS = {
    "zone.occupancy",
    "manual.wind",
    "manual.visibility",
    "manual.precipitation",
    "manual.area_cleared",
}


def validate_finding(f: Finding) -> None:
    """Validate that a finding complies with Constitution 2.III explainability invariants."""
    if not f.module or not f.module.strip():
        raise InadmissibleFinding("Finding module is missing or empty")
    if not f.check_id or not f.check_id.strip():
        raise InadmissibleFinding("Finding check_id is missing or empty")
    if not isinstance(f.severity, Severity):
        raise InadmissibleFinding(f"Finding severity invalid: {f.severity}")
    if not f.message or not f.message.strip():
        raise InadmissibleFinding("Finding message is missing or empty")
    if not (0.0 <= f.confidence <= 1.0):
        raise InadmissibleFinding(
            f"Finding confidence must be between 0.0 and 1.0, got: {f.confidence}"
        )
    if not f.metrics:
        raise InadmissibleFinding("Finding metrics cannot be empty (Constitution 2.III)")

    # Visual checks must carry an overlay unless in the documented exemption set
    is_exempt = f.check_id.startswith("manual.") or f.check_id in OVERLAY_EXEMPT_CHECKS
    if not is_exempt and f.overlay is None and not f.degraded:
        raise InadmissibleFinding(
            f"Visual check '{f.check_id}' must carry an overlay (Constitution 2.III)"
        )


@dataclass(frozen=True)
class Thresholds:
    fin_angle_warning_deg: float = 3.0
    fin_angle_critical_deg: float = 6.0
    fin_angle_error_margin_deg: float = 1.5
    wind_warning_ms: float = 10.0
    wind_critical_ms: float = 15.0
    poor_visibility_severity: Severity = Severity.WARNING
    heavy_precipitation_severity: Severity = Severity.WARNING
    area_not_cleared_severity: Severity = Severity.CRITICAL
    object_in_zone_severity: Severity = Severity.CRITICAL
    motion_sensitivity: float = 0.5
    detector_conf: float = 0.25
    detector_iou: float = 0.45
    zone_occupancy: bool = True


@dataclass(frozen=True)
class ManualInputSet:
    wind_speed_ms: float | None = None
    visibility: Literal["good", "moderate", "poor"] | None = None
    precipitation: Literal["none", "light", "heavy"] | None = None
    area_cleared: bool | None = None
    notes: str | None = None


@dataclass(frozen=True)
class StepResult:
    position: int
    step_key: str
    status: Literal["pending", "running", "passed", "failed", "blocked"]
    finding_count: int = 0


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    risk_score: int
    findings: tuple[Finding, ...]
    checklist: tuple[StepResult, ...]
    reasons: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    computed_at: datetime
