"""Pydantic schemas for LaunchGuard AI API contracts (contracts/api.md, Constitution 3.I)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from rule_engine.types import Severity, Verdict

# --- Common & Error Schemas ---


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Domain Sub-Schemas ---


class MeasurementSchema(BaseModel):
    name: str
    value: float
    unit: str
    error_margin: float | None = None
    threshold: float | None = None


class OverlaySchema(BaseModel):
    kind: str
    check_id: str
    points: list[list[float]] = Field(default_factory=list)
    radius: float | None = None
    start_deg: float | None = None
    end_deg: float | None = None
    label: str | None = None


class FindingSchema(BaseModel):
    module: str
    check_id: str
    severity: Severity
    message: str
    confidence: float
    metrics: list[MeasurementSchema] = Field(default_factory=list)
    overlay: OverlaySchema | None = None
    step_position: int = 0
    degraded: bool = False
    low_confidence_critical: bool = False
    near_threshold_note: str | None = None


class ChecklistStepSchema(BaseModel):
    position: int
    step_key: str
    label: str
    status: str
    finding_count: int = 0


class ReasonSchema(BaseModel):
    check_id: str
    severity: Severity
    message: str
    confidence: float
    ambiguous: bool = False


class ActionSchema(BaseModel):
    check_id: str
    action: str


class NarrativeSchema(BaseModel):
    status: str
    text: str | None = None
    model: str | None = None


# --- Run Lifecycle Schemas ---


class CreateRunResponse(BaseModel):
    run_id: str
    mode: str
    status: str
    stream_url: str
    expected_steps: list[str]


class RunDetailSource(BaseModel):
    width: int | None = None
    height: int | None = None
    url: str | None = None


class RunDetailResponse(BaseModel):
    run_id: str
    mode: str
    source_type: str
    status: str
    status_reason: str | None = None
    verdict: Verdict | None = None
    risk_score: int | None = None
    created_at: str
    completed_at: str | None = None
    thresholds: dict[str, Any] = Field(default_factory=dict)
    source: RunDetailSource = Field(default_factory=RunDetailSource)


class RunListItem(BaseModel):
    run_id: str
    verdict: Verdict | None = None
    risk_score: int | None = None
    status: str
    created_at: str
    max_severity: Severity | None = None


class RunListResponse(BaseModel):
    total: int
    items: list[RunListItem]


class LatestRunSummaryResponse(BaseModel):
    verdict: Verdict | None = None
    risk_score: int | None = None
    checklist: list[ChecklistStepSchema] = Field(default_factory=list)
    latest_runs: list[RunListItem] = Field(default_factory=list)


# --- Manual Inputs Schemas ---


class InputFieldSchema(BaseModel):
    name: str
    label: str
    type: str
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    options: list[str] | None = None
    max_length: int | None = None
    required: bool = True


class RequiredInputsResponse(BaseModel):
    run_id: str
    missing: list[str]
    fields: list[InputFieldSchema]


class ManualInputPayload(BaseModel):
    wind_speed_ms: float | None = None
    visibility: str | None = None
    precipitation: str | None = None
    area_cleared: bool | None = None
    notes: str | None = None


class ManualInputsSubmissionResponse(BaseModel):
    status: str
    missing: list[str]
    fields: list[InputFieldSchema]


# --- Launchpad Monitor Schemas ---


class ZonePolygonPayload(BaseModel):
    points: list[list[float]]
    label: str | None = None


class DangerZoneResponse(BaseModel):
    run_id: str
    points: list[list[float]]
    source_width: int
    source_height: int
    label: str | None = None


class DeleteZoneResponse(BaseModel):
    deleted: bool = True


class FrameAnalysisResponse(BaseModel):
    seq: int
    zone_status: str
    processing_ms: float
    frame_width: int
    frame_height: int
    findings: list[FindingSchema]


class MonitorLogEntry(BaseModel):
    at: str
    zone_status: str
    check_ids: list[str]
    max_severity: str


class MonitorLogResponse(BaseModel):
    entries: list[MonitorLogEntry]


# --- Report & Sharing Schemas ---


class ReportResponse(BaseModel):
    report_id: str
    run_id: str
    verdict: Verdict
    risk_score: int
    verdict_attribution: str
    disclaimer: str
    checklist: list[ChecklistStepSchema]
    reasons: list[ReasonSchema]
    recommended_actions: list[ActionSchema]
    findings: list[FindingSchema]
    narrative: NarrativeSchema
    annotated_image_url: str | None = None
    generated_at: str
    share_token: str | None = None


class ShareTokenResponse(BaseModel):
    token: str
    url: str
    read_only: bool = True
    created_at: str


class PublicReportResponse(BaseModel):
    report_id: str
    run_id: str
    verdict: Verdict
    risk_score: int
    disclaimer: str
    checklist: list[ChecklistStepSchema]
    reasons: list[ReasonSchema]
    recommended_actions: list[ActionSchema]
    narrative: NarrativeSchema
    annotated_image_url: str | None = None
    generated_at: str


# --- Demo Scenarios Schemas ---


class DemoScenarioItem(BaseModel):
    key: str
    label: str
    expected_verdict: Verdict


class DemoScenariosResponse(BaseModel):
    scenarios: list[DemoScenarioItem]


# --- Event Streaming Schemas ---


class EventMessageResponse(BaseModel):
    seq: int
    event_type: str
    payload: dict[str, Any]
    at: str
