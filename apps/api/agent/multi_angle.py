"""Bounded quadrant orchestration; detection stays in CV and verdicts in the rule engine."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray
from sqlalchemy import select

from agent.report import assemble_early_report
from agent.tools import (
    check_fin_alignment,
    check_launchpad_clear,
    compare_reference_evidence,
    inspect_body,
)
from app.events import broadcaster
from app.schemas import FindingSchema
from cv.annotate import render_annotated_image
from cv.frameio import decode_image
from cv.subject import locate_rocket, unavailable
from db.base import async_session_factory
from db.models import (
    InspectionImageModel,
    NarrativeStatus,
    RocketReferenceModel,
    RunModel,
    RunStatus,
    StepStatus,
)
from db.repo import append_finding, update_checklist_step, update_run
from rule_engine.config import apply_confidence_floor
from rule_engine.types import (
    QUADRANTS,
    Finding,
    Measurement,
    Quadrant,
    Severity,
    Thresholds,
    validate_finding,
)
from rule_engine.verdict import make_decision

logger = logging.getLogger(__name__)
CHECK_TIMEOUT_S = 10.0
Detector = Callable[[NDArray[np.uint8], Thresholds], list[Finding]]


async def evaluate_reference(
    current_path: str | None,
    reference_path: str | None,
    quadrant: Quadrant,
) -> tuple[Finding, NDArray[np.uint8] | None, NDArray[np.uint8] | None]:
    """Run the pure reference tool with a timeout and return derived visual evidence."""
    if current_path is None:
        return (
            Finding(
                module="cv.reference",
                check_id="reference.current_missing",
                severity=Severity.WARNING,
                message=f"{quadrant.title()}: Current image is missing; reference comparison "
                "requires manual review.",
                confidence=0.0,
                metrics=(Measurement("comparison_available", 0.0, "status"),),
                step_position=1,
                degraded=True,
                quadrant=quadrant,
            ),
            None,
            None,
        )
    if reference_path is None or not Path(reference_path).is_file():
        return (
            Finding(
                module="cv.reference",
                check_id="reference.missing_baseline",
                severity=Severity.WARNING,
                message=f"{quadrant.title()}: Golden reference is missing; manual baseline "
                "comparison required.",
                confidence=0.0,
                metrics=(Measurement("baseline_available", 0.0, "status"),),
                step_position=1,
                degraded=True,
                quadrant=quadrant,
            ),
            None,
            None,
        )

    def execute() -> tuple[Finding, NDArray[np.uint8] | None, NDArray[np.uint8] | None]:
        reference = decode_image(Path(reference_path).read_bytes())
        current = decode_image(Path(current_path).read_bytes())
        if locate_rocket(reference) is None:
            return replace(unavailable(
                "cv.reference", "reference.subject_unverified", 1,
                f"{quadrant.title()}: Stored baseline is not a supported rocket-like view.",
            ), quadrant=quadrant), None, None
        evidence = compare_reference_evidence(reference, current, quadrant)
        return evidence.finding, evidence.aligned_current, evidence.heatmap_bgr

    try:
        finding, aligned, heatmap = await asyncio.wait_for(
            asyncio.to_thread(execute), timeout=CHECK_TIMEOUT_S
        )
        finding = apply_confidence_floor(finding)
        validate_finding(finding)
        return finding, aligned, heatmap
    except TimeoutError:
        reason = "timed out"
    except Exception as exc:
        logger.warning("%s/reference unavailable: %s", quadrant, type(exc).__name__)
        reason = f"failed ({type(exc).__name__})"
    return (
        Finding(
            module="cv.reference",
            check_id="reference.analysis_failed",
            severity=Severity.WARNING,
            message=f"{quadrant.title()}: Reference comparison {reason}; manual baseline "
            "comparison required.",
            confidence=0.0,
            metrics=(Measurement("comparison_available", 0.0, "status"),),
            step_position=1,
            degraded=True,
            quadrant=quadrant,
        ),
        None,
        None,
    )


def _write_jpeg(path: Path, image: NDArray[np.uint8]) -> None:
    success, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not success:
        raise ValueError("Could not encode reference evidence")
    path.write_bytes(bytes(buffer))


async def evaluate_quadrant(
    path: str | None,
    quadrant: Quadrant,
    detector: Detector,
    step: int,
    key: str,
    thresholds: Thresholds,
) -> list[Finding]:
    """Retain every finding and degrade unavailable, empty, or invalid tool results."""

    def execute() -> list[Finding]:
        if path is None:
            raise FileNotFoundError("Missing quadrant image")
        image = decode_image(Path(path).read_bytes())
        if key == "launchpad_area" and locate_rocket(image) is None:
            return [unavailable(
                "cv.pad", "pad.subject_unverified", 3,
                "Unsupported rocket inspection view; pad assessment was not performed.",
            )]
        findings = detector(image, thresholds)
        if not findings:
            raise ValueError("No findings returned")
        return findings

    def unavailable(reason: str) -> Finding:
        return Finding(
            module=f"cv.{key}",
            check_id=f"{key}.unavailable",
            severity=Severity.WARNING,
            confidence=0.0,
            degraded=True,
            message=f"{quadrant.title()}: {reason}; manual inspection required.",
            metrics=(Measurement("evaluated", 0.0, "status"),),
            step_position=step,
            quadrant=quadrant,
        )

    try:
        findings = await asyncio.wait_for(asyncio.to_thread(execute), timeout=CHECK_TIMEOUT_S)
    except Exception as exc:
        logger.warning("%s/%s unavailable: %s", quadrant, key, type(exc).__name__)
        reason = "Image missing" if path is None else f"Check unavailable ({type(exc).__name__})"
        return [unavailable(reason)]

    result: list[Finding] = []
    for finding in findings:
        try:
            finding = apply_confidence_floor(
                replace(
                    finding,
                    quadrant=quadrant,
                    step_position=step,
                    message=f"{quadrant.title()}: {finding.message}",
                )
            )
            validate_finding(finding)
            result.append(finding)
        except Exception:
            result.append(unavailable("Invalid tool result"))
    return result


async def run_multi_angle(run_id: str) -> None:
    """Stream and persist all checks, then ask the deterministic engine for one verdict."""
    async with async_session_factory() as session:
        try:
            records = list(
                (
                    await session.scalars(
                        select(InspectionImageModel).where(InspectionImageModel.run_id == run_id)
                    )
                ).all()
            )
            captures = {record.quadrant: record for record in records}
            run = await session.get(RunModel, run_id)
            reference_records: list[RocketReferenceModel] = []
            if run and run.rocket_id:
                reference_records = list(
                    (
                        await session.scalars(
                            select(RocketReferenceModel).where(
                                RocketReferenceModel.rocket_id == run.rocket_id
                            )
                        )
                    ).all()
                )
            references = {record.quadrant: record.image_path for record in reference_records}
            thresholds = Thresholds()
            findings: list[Finding] = []
            checks: tuple[tuple[int, str, Detector], ...] = (
                (1, "body", inspect_body),
                (2, "fins", check_fin_alignment),
                (
                    3,
                    "launchpad_area",
                    lambda image, cfg: check_launchpad_clear(image, thresholds=cfg),
                ),
            )
            for step, key, detector in checks:
                await update_checklist_step(session, run_id, step, StepStatus.RUNNING)
                await broadcaster.publish(
                    run_id,
                    "checklist.step.started",
                    {
                        "position": step,
                        "step_key": key,
                        "label": key.replace("_", " "),
                    },
                    session=session,
                )
                await session.commit()
                step_findings: list[Finding] = []
                for quadrant in QUADRANTS:
                    record = captures.get(quadrant)
                    path = record.image_path if record else None
                    batch = await evaluate_quadrant(path, quadrant, detector, step, key, thresholds)
                    if step == 1:
                        reference_finding, aligned, heatmap = await evaluate_reference(
                            path, references.get(quadrant), quadrant
                        )
                        batch.append(reference_finding)
                        if (
                            record
                            and record.image_path
                            and aligned is not None
                            and heatmap is not None
                        ):
                            base_path = Path(record.image_path)
                            await asyncio.to_thread(
                                _write_jpeg, base_path.with_suffix(".aligned.jpg"), aligned
                            )
                            await asyncio.to_thread(
                                _write_jpeg, base_path.with_suffix(".heatmap.jpg"), heatmap
                            )
                    for finding in batch:
                        await append_finding(session, run_id, finding)
                        payload = FindingSchema.model_validate(
                            finding, from_attributes=True
                        ).model_dump(mode="json")
                        await broadcaster.publish(
                            run_id, "finding.raised", payload, session=session
                        )
                    step_findings.extend(batch)
                    await session.commit()
                findings.extend(step_findings)
                step_status = (
                    StepStatus.FAILED
                    if any(f.severity != Severity.OK for f in step_findings)
                    else StepStatus.PASSED
                )
                await update_checklist_step(session, run_id, step, step_status)
                await broadcaster.publish(
                    run_id,
                    "checklist.step.finished",
                    {
                        "position": step,
                        "step_key": key,
                        "status": step_status.value,
                        "finding_count": len(step_findings),
                    },
                    session=session,
                )
                await session.commit()

            for record in records:
                if record.image_path:
                    try:
                        image = await asyncio.to_thread(
                            decode_image, Path(record.image_path).read_bytes()
                        )
                        annotated = await asyncio.wait_for(
                            asyncio.to_thread(
                                render_annotated_image,
                                image,
                                [f for f in findings if f.quadrant == record.quadrant],
                            ),
                            timeout=CHECK_TIMEOUT_S,
                        )
                        Path(record.image_path).with_suffix(".annotated.jpg").write_bytes(annotated)
                    except Exception:
                        # An unavailable annotation must not discard a detected critical defect.
                        finding = Finding(
                            module="cv.annotation",
                            check_id="annotation.unavailable",
                            severity=Severity.WARNING,
                            confidence=0.0,
                            degraded=True,
                            message=f"{record.quadrant.title()}: Annotation unavailable; "
                            "review original image and measured findings.",
                            metrics=(Measurement("annotation_available", 0.0, "status"),),
                            step_position=1,
                            quadrant=record.quadrant,
                        )
                        findings.append(finding)
                        await append_finding(session, run_id, finding)
                        await broadcaster.publish(
                            run_id,
                            "finding.raised",
                            FindingSchema.model_validate(finding, from_attributes=True).model_dump(
                                mode="json"
                            ),
                            session=session,
                        )

            decision = make_decision(findings, manual_inputs=None, thresholds=thresholds)
            for checklist_step in decision.checklist:
                await update_checklist_step(
                    session, run_id, checklist_step.position, StepStatus(checklist_step.status)
                )
            report = await assemble_early_report(session, run_id, decision)
            report.narrative_status = NarrativeStatus.UNAVAILABLE
            await update_run(
                session,
                run_id,
                status=RunStatus.COMPLETED,
                verdict=decision.verdict,
                risk_score=decision.risk_score,
                completed=True,
            )
            await broadcaster.publish(
                run_id,
                "run.completed",
                {
                    "run_id": run_id,
                    "verdict": decision.verdict.value,
                    "risk_score": decision.risk_score,
                    "report_id": report.id,
                    "reasons": report.reasons_json,
                },
                session=session,
            )
            await broadcaster.publish(
                run_id,
                "report.narrative_ready",
                {
                    "narrative": {"status": "unavailable", "text": None, "model": None},
                },
                session=session,
            )
            await session.commit()
        except Exception:
            logger.exception("Multi-angle run %s failed", run_id)
            await session.rollback()
            await update_run(
                session,
                run_id,
                status=RunStatus.FAILED,
                status_reason="Inspection could not be completed.",
            )
            await broadcaster.publish(
                run_id,
                "run.failed",
                {
                    "reason": "processing_error",
                    "message": "Inspection could not be completed.",
                },
                session=session,
            )
            await session.commit()
