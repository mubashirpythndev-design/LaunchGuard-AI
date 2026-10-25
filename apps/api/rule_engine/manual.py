"""Manual inputs evaluation and checklist rules (Constitution 2.I, 2.II).

Evaluates weather inputs (wind, visibility, precipitation) and range area clearance.
Missing mandatory inputs force a HOLD verdict.
"""

from __future__ import annotations

from collections.abc import Sequence

from rule_engine.config import DEFAULT_THRESHOLDS
from rule_engine.types import Finding, ManualInputSet, Measurement, Severity, Thresholds

MANDATORY_FIELDS: Sequence[str] = (
    "wind_speed_ms",
    "visibility",
    "precipitation",
    "area_cleared",
)


def get_missing_mandatory_inputs(inputs: ManualInputSet | None) -> list[str]:
    """Identify which mandatory manual checklist inputs are missing."""
    if inputs is None:
        return list(MANDATORY_FIELDS)
    missing: list[str] = []
    if inputs.wind_speed_ms is None:
        missing.append("wind_speed_ms")
    if inputs.visibility is None:
        missing.append("visibility")
    if inputs.precipitation is None:
        missing.append("precipitation")
    if inputs.area_cleared is None:
        missing.append("area_cleared")
    return missing


def evaluate_manual_inputs(
    inputs: ManualInputSet | None,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
) -> list[Finding]:
    """Evaluate manual checklist inputs against configured thresholds."""
    findings: list[Finding] = []
    missing = get_missing_mandatory_inputs(inputs)

    if missing:
        findings.append(
            Finding(
                module="rule_engine.manual",
                check_id="manual.missing_inputs",
                severity=Severity.WARNING,
                message=f"Mandatory checklist inputs missing: {', '.join(missing)}",
                confidence=1.0,
                metrics=(
                    Measurement(
                        name="missing_fields_count",
                        value=float(len(missing)),
                        unit="fields",
                    ),
                ),
                step_position=4,
            )
        )

    if inputs is None:
        return findings

    # 1. Wind speed
    if inputs.wind_speed_ms is not None:
        w = inputs.wind_speed_ms
        if w > thresholds.wind_critical_ms:
            sev = Severity.CRITICAL
            thresh = thresholds.wind_critical_ms
        elif w > thresholds.wind_warning_ms:
            sev = Severity.WARNING
            thresh = thresholds.wind_warning_ms
        else:
            sev = Severity.OK
            thresh = thresholds.wind_warning_ms

        findings.append(
            Finding(
                module="rule_engine.manual",
                check_id="manual.wind",
                severity=sev,
                message=(
                    f"Surface wind speed {w:.1f} m/s "
                    f"(warn >{thresholds.wind_warning_ms:.1f}, "
                    f"crit >{thresholds.wind_critical_ms:.1f})"
                ),
                confidence=1.0,
                metrics=(
                    Measurement(
                        name="wind_speed",
                        value=w,
                        unit="m/s",
                        threshold=thresh,
                    ),
                ),
                step_position=4,
            )
        )

    # 2. Visibility
    if inputs.visibility is not None:
        vis_sev = (
            thresholds.poor_visibility_severity if inputs.visibility == "poor" else Severity.OK
        )
        findings.append(
            Finding(
                module="rule_engine.manual",
                check_id="manual.visibility",
                severity=vis_sev,
                message=f"Atmospheric visibility appears {inputs.visibility}",
                confidence=1.0,
                metrics=(
                    Measurement(
                        name="visibility_rank",
                        value=1.0 if inputs.visibility == "poor" else 3.0,
                        unit="grade",
                    ),
                ),
                step_position=4,
            )
        )

    # 3. Precipitation
    if inputs.precipitation is not None:
        precip_sev = (
            thresholds.heavy_precipitation_severity
            if inputs.precipitation == "heavy"
            else Severity.OK
        )
        findings.append(
            Finding(
                module="rule_engine.manual",
                check_id="manual.precipitation",
                severity=precip_sev,
                message=f"Precipitation condition appears {inputs.precipitation}",
                confidence=1.0,
                metrics=(
                    Measurement(
                        name="precipitation_intensity",
                        value=3.0 if inputs.precipitation == "heavy" else 0.0,
                        unit="grade",
                    ),
                ),
                step_position=4,
            )
        )

    # 4. Area cleared
    if inputs.area_cleared is not None:
        area_sev = Severity.OK if inputs.area_cleared else thresholds.area_not_cleared_severity
        findings.append(
            Finding(
                module="rule_engine.manual",
                check_id="manual.area_cleared",
                severity=area_sev,
                message=(
                    "Launch area clearance confirmed"
                    if inputs.area_cleared
                    else "Launch area clearance NOT confirmed by safety officer"
                ),
                confidence=1.0,
                metrics=(
                    Measurement(
                        name="area_cleared",
                        value=1.0 if inputs.area_cleared else 0.0,
                        unit="bool",
                    ),
                ),
                step_position=4,
            )
        )

    return findings
