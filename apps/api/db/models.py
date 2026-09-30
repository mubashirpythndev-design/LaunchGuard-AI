"""SQLAlchemy 2 database models for LaunchGuard AI (Constitution 3.V, data-model.md)."""
from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from rule_engine.types import Severity, Verdict


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


def generate_uuid() -> str:
    """Return a UUIDv4 string."""
    return str(uuid.uuid4())


class RunMode(enum.StrEnum):
    INSPECTION = "inspection"
    MONITOR = "monitor"
    DEMO = "demo"


class RunStatus(enum.StrEnum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(enum.StrEnum):
    IMAGE_UPLOAD = "image_upload"
    VIDEO_UPLOAD = "video_upload"
    LIVE_STREAM = "live_stream"
    DEMO_BUNDLE = "demo_bundle"


class StepStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class NarrativeStatus(enum.StrEnum):
    PENDING = "pending"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class RunModel(Base):
    """Execution run entity."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    mode: Mapped[RunMode] = mapped_column(
        sa.Enum(RunMode, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_type: Mapped[SourceType] = mapped_column(
        sa.Enum(SourceType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        sa.Enum(RunStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RunStatus.RUNNING,
    )
    status_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    verdict: Mapped[Verdict | None] = mapped_column(
        sa.Enum(Verdict, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    risk_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    thresholds_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False, default=dict)
    frame_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    findings: Mapped[list[FindingModel]] = relationship(
        "FindingModel", back_populates="run", cascade="all, delete-orphan"
    )
    danger_zone: Mapped[DangerZoneModel | None] = relationship(
        "DangerZoneModel", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
    checklist_steps: Mapped[list[ChecklistStepModel]] = relationship(
        "ChecklistStepModel", back_populates="run", cascade="all, delete-orphan"
    )
    manual_inputs: Mapped[list[ManualInputModel]] = relationship(
        "ManualInputModel", back_populates="run", cascade="all, delete-orphan"
    )
    events: Mapped[list[RunEventModel]] = relationship(
        "RunEventModel", back_populates="run", cascade="all, delete-orphan"
    )
    report: Mapped[ReportModel | None] = relationship(
        "ReportModel", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_runs_status", "status"),
        Index("ix_runs_created_at_desc", created_at.desc()),
    )


class FindingModel(Base):
    """Individual inspection or check finding."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    check_id: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        sa.Enum(Severity, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    metrics_json: Mapped[list[dict[str, Any]]] = mapped_column(
        sa.JSON, nullable=False, default=list
    )
    overlay_json: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    step_position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    degraded: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    low_confidence_critical: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    near_threshold_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[RunModel] = relationship("RunModel", back_populates="findings")

    __table_args__ = (
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_finding_confidence"),
    )


class DangerZoneModel(Base):
    """User-defined or preset safety exclusion zone polygon."""

    __tablename__ = "danger_zones"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    points_json: Mapped[list[list[float]]] = mapped_column(sa.JSON, nullable=False)
    source_width: Mapped[int] = mapped_column(Integer, nullable=False)
    source_height: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    run: Mapped[RunModel] = relationship("RunModel", back_populates="danger_zone")


class ChecklistStepModel(Base):
    """Execution step status tracking entity."""

    __tablename__ = "checklist_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    step_key: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[StepStatus] = mapped_column(
        sa.Enum(StepStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=StepStatus.PENDING,
    )
    finding_ids_json: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    required_inputs_json: Mapped[list[str] | None] = mapped_column(sa.JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped[RunModel] = relationship("RunModel", back_populates="checklist_steps")

    __table_args__ = (
        UniqueConstraint("run_id", "position", name="uq_checklist_steps_run_position"),
    )


class ManualInputModel(Base):
    """Manual environmental or range clearance input."""

    __tablename__ = "manual_inputs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    value_json: Mapped[Any] = mapped_column(sa.JSON, nullable=False)
    rule_fired: Mapped[Severity | None] = mapped_column(
        sa.Enum(Severity, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[RunModel] = relationship("RunModel", back_populates="manual_inputs")

    __table_args__ = (
        UniqueConstraint("run_id", "field", name="uq_manual_inputs_run_field"),
    )


class RunEventModel(Base):
    """Monotonic event log for live streaming and SSE reconnect."""

    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[RunModel] = relationship("RunModel", back_populates="events")

    __table_args__ = (
        UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq"),
    )


class ReportModel(Base):
    """Immutable audit report generated upon inspection/run completion."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    verdict: Mapped[Verdict] = mapped_column(
        sa.Enum(Verdict, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    risk_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reasons_json: Mapped[list[str]] = mapped_column(sa.JSON, nullable=False, default=list)
    checklist_json: Mapped[list[dict[str, Any]]] = mapped_column(
        sa.JSON, nullable=False, default=list
    )
    recommended_actions_json: Mapped[list[str]] = mapped_column(
        sa.JSON, nullable=False, default=list
    )
    narrative_status: Mapped[NarrativeStatus] = mapped_column(
        sa.Enum(NarrativeStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=NarrativeStatus.PENDING,
    )
    narrative_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    narrative_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    disclaimer: Mapped[str] = mapped_column(String(200), nullable=False)
    share_token: Mapped[str | None] = mapped_column(String(43), nullable=True, unique=True)
    annotated_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    run: Mapped[RunModel] = relationship("RunModel", back_populates="report")


class DemoScenarioModel(Base):
    """Bundled offline demo scenario entity."""

    __tablename__ = "demo_scenarios"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    expected_verdict: Mapped[Verdict] = mapped_column(
        sa.Enum(Verdict, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    manual_inputs_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON, nullable=False)
    zone_points_json: Mapped[list[list[float]] | None] = mapped_column(sa.JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
