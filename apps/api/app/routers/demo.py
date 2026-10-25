"""Demo mode scenarios API router (Constitution 6.I, contracts/api.md, FR-036)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from agent.narrative import build_narrative_context, generate_narrative
from agent.report import assemble_early_report, complete_report_narrative
from agent.tools import check_fin_alignment, check_launchpad_clear, inspect_body
from app.config import get_settings
from app.events import broadcaster
from app.schemas import (
    CreateRunResponse,
    DemoScenarioItem,
    DemoScenariosResponse,
)
from cv.annotate import render_annotated_image
from cv.frameio import decode_image
from db.base import get_db
from db.models import RunMode, RunStatus, SourceType, StepStatus
from db.repo import (
    append_finding,
    create_run,
    get_demo_scenario,
    init_checklist_steps,
    list_demo_scenarios,
    update_checklist_step,
    update_run,
    upsert_danger_zone,
    upsert_manual_input,
)
from rule_engine.manual import evaluate_manual_inputs
from rule_engine.types import (
    Finding,
    ManualInputSet,
    Thresholds,
)
from rule_engine.verdict import make_decision

router = APIRouter(prefix="/api/demo", tags=["demo"])

EXPECTED_STEPS = ["body", "fins", "launchpad_area", "weather_manual", "decision"]


def _serialize_finding(f: Finding) -> dict[str, Any]:
    return {
        "module": f.module,
        "check_id": f.check_id,
        "severity": f.severity.value,
        "message": f.message,
        "confidence": f.confidence,
        "metrics": [
            {
                "name": m.name,
                "value": m.value,
                "unit": m.unit,
                "error_margin": m.error_margin,
                "threshold": m.threshold,
            }
            for m in f.metrics
        ],
        "overlay": (
            {
                "kind": f.overlay.kind.value,
                "check_id": f.overlay.check_id,
                "points": [list(pt) for pt in f.overlay.points],
                "radius": f.overlay.radius,
                "start_deg": f.overlay.start_deg,
                "end_deg": f.overlay.end_deg,
                "label": f.overlay.label,
            }
            if f.overlay
            else None
        ),
        "step_position": f.step_position,
        "degraded": f.degraded,
        "low_confidence_critical": f.low_confidence_critical,
        "near_threshold_note": f.near_threshold_note,
    }


@router.get("/scenarios", response_model=DemoScenariosResponse)
async def get_demo_scenarios(
    session: AsyncSession = Depends(get_db),
) -> DemoScenariosResponse:
    """List all available pre-configured demo scenarios."""
    records = await list_demo_scenarios(session)
    return DemoScenariosResponse(
        scenarios=[
            DemoScenarioItem(
                key=s.key,
                label=s.label,
                expected_verdict=s.expected_verdict,
            )
            for s in records
        ]
    )


@router.post(
    "/scenarios/{key}/run",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRunResponse,
)
async def trigger_demo_scenario(
    key: str,
    session: AsyncSession = Depends(get_db),
) -> CreateRunResponse:
    """Launch a pipeline run using bundled scenario data through identical pipeline (FR-036)."""
    scenario = await get_demo_scenario(session, key)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo scenario '{key}' not found.",
        )

    settings = get_settings()

    # Resolve fixture image path
    fixture_dir = Path(__file__).parents[2] / "tests" / "fixtures" / "images"
    possible_paths = [
        Path(settings.media_root) / scenario.source_ref,
        fixture_dir / Path(scenario.source_ref).name,
        Path(__file__).parents[3] / "apps" / "web" / "public" / scenario.source_ref,
    ]
    img_path = next((p for p in possible_paths if p.exists()), None)
    if not img_path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fixture image '{scenario.source_ref}' not found on server.",
        )

    content = img_path.read_bytes()
    img = decode_image(content)
    h, w = img.shape[:2]
    run_id = str(uuid.uuid4())
    thresholds = Thresholds()

    # Persist raw image to media runs
    media_dir = Path(settings.media_root) / "runs"
    media_dir.mkdir(parents=True, exist_ok=True)
    raw_image_path = media_dir / f"{run_id}.jpg"
    raw_image_path.write_bytes(content)

    # 1. Create run record in DB
    await create_run(
        session=session,
        run_id=run_id,
        mode=RunMode.INSPECTION,
        source_type=SourceType.IMAGE_UPLOAD,
        source_ref=str(raw_image_path),
        frame_width=w,
        frame_height=h,
    )
    await init_checklist_steps(session, run_id)

    # Save danger zone if present
    if scenario.zone_points_json:
        await upsert_danger_zone(
            session=session,
            run_id=run_id,
            points=scenario.zone_points_json,
            source_width=w,
            source_height=h,
            label="Demo Exclusion Zone",
        )

    # 2. Publish run.started
    await broadcaster.publish(
        run_id,
        "run.started",
        {
            "run_id": run_id,
            "mode": "inspection",
            "source_type": "image_upload",
            "steps": [
                {"position": 1, "step_key": "body", "label": "Inspect body"},
                {"position": 2, "step_key": "fins", "label": "Check fins"},
                {"position": 3, "step_key": "launchpad_area", "label": "Check launchpad area"},
                {"position": 4, "step_key": "weather_manual", "label": "Weather & manual inputs"},
                {"position": 5, "step_key": "decision", "label": "Generate decision"},
            ],
        },
        session=session,
    )

    # 3. Step 1: Body inspection
    await broadcaster.publish(
        run_id,
        "checklist.step.started",
        {"position": 1, "step_key": "body", "label": "Inspect body"},
        session=session,
    )
    await update_checklist_step(session, run_id, 1, StepStatus.RUNNING)
    body_findings: list[Finding] = inspect_body(img, thresholds)
    for f in body_findings:
        await append_finding(session, run_id, f)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(f), session=session)

    step1_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in body_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 1, step1_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {
            "position": 1,
            "step_key": "body",
            "status": step1_status.value,
            "finding_count": len(body_findings),
        },
        session=session,
    )

    # 4. Step 2: Fin alignment
    await broadcaster.publish(
        run_id,
        "checklist.step.started",
        {"position": 2, "step_key": "fins", "label": "Check fins"},
        session=session,
    )
    await update_checklist_step(session, run_id, 2, StepStatus.RUNNING)
    fin_findings: list[Finding] = check_fin_alignment(img, thresholds)
    for f in fin_findings:
        await append_finding(session, run_id, f)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(f), session=session)

    step2_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in fin_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 2, step2_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {
            "position": 2,
            "step_key": "fins",
            "status": step2_status.value,
            "finding_count": len(fin_findings),
        },
        session=session,
    )

    # 5. Step 3: Launchpad area / zone
    await broadcaster.publish(
        run_id,
        "checklist.step.started",
        {"position": 3, "step_key": "launchpad_area", "label": "Check launchpad area"},
        session=session,
    )
    await update_checklist_step(session, run_id, 3, StepStatus.RUNNING)
    danger_zone = (
        [(float(p[0]), float(p[1])) for p in scenario.zone_points_json]
        if scenario.zone_points_json
        else None
    )
    pad_findings: list[Finding] = check_launchpad_clear(
        img, danger_zone=danger_zone, thresholds=thresholds
    )
    for f in pad_findings:
        await append_finding(session, run_id, f)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(f), session=session)

    step3_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in pad_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 3, step3_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {
            "position": 3,
            "step_key": "launchpad_area",
            "status": step3_status.value,
            "finding_count": len(pad_findings),
        },
        session=session,
    )

    # 6. Step 4: Weather & manual inputs (bundled, never pauses in demo)
    await broadcaster.publish(
        run_id,
        "checklist.step.started",
        {"position": 4, "step_key": "weather_manual", "label": "Weather & manual inputs"},
        session=session,
    )
    await update_checklist_step(session, run_id, 4, StepStatus.RUNNING)
    manual_dict = scenario.manual_inputs_json or {}
    for k, v in manual_dict.items():
        await upsert_manual_input(session, run_id, k, v)

    manual_set = ManualInputSet(
        wind_speed_ms=manual_dict.get("wind_speed_ms"),
        visibility=manual_dict.get("visibility"),
        precipitation=manual_dict.get("precipitation"),
        area_cleared=manual_dict.get("area_cleared"),
        notes=manual_dict.get("notes"),
    )
    manual_findings = evaluate_manual_inputs(manual_set)
    for mf in manual_findings:
        await append_finding(session, run_id, mf)
        await broadcaster.publish(run_id, "finding.raised", _serialize_finding(mf), session=session)

    step4_status = (
        StepStatus.FAILED
        if any(f.severity.value != "ok" for f in manual_findings)
        else StepStatus.PASSED
    )
    await update_checklist_step(session, run_id, 4, step4_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {
            "position": 4,
            "step_key": "weather_manual",
            "status": step4_status.value,
            "finding_count": len(manual_findings),
        },
        session=session,
    )

    # 7. Step 5: Generate decision
    await broadcaster.publish(
        run_id,
        "checklist.step.started",
        {"position": 5, "step_key": "decision", "label": "Generate decision"},
        session=session,
    )
    await update_checklist_step(session, run_id, 5, StepStatus.RUNNING)

    all_findings = body_findings + fin_findings + pad_findings + manual_findings
    decision = make_decision(all_findings, manual_inputs=manual_set, thresholds=thresholds)

    step5_status = (
        StepStatus.PASSED if decision.verdict.value == "GO" else StepStatus.FAILED
    )
    await update_checklist_step(session, run_id, 5, step5_status)
    await broadcaster.publish(
        run_id,
        "checklist.step.finished",
        {
            "position": 5,
            "step_key": "decision",
            "status": step5_status.value,
            "finding_count": 0,
        },
        session=session,
    )

    # 8. Render annotated composite image
    annotated_bytes = render_annotated_image(img, all_findings)
    annotated_path = media_dir / f"{run_id}_annotated.jpg"
    annotated_path.write_bytes(annotated_bytes)
    annotated_url = f"/api/runs/{run_id}/annotated.png"

    # Persist early report (verdict and reasons fixed before model call)
    report = await assemble_early_report(
        session, run_id=run_id, decision=decision, annotated_ref=annotated_url
    )

    # Update run status
    await update_run(
        session,
        run_id=run_id,
        status=RunStatus.COMPLETED,
        verdict=decision.verdict,
        risk_score=decision.risk_score,
        completed=True,
    )

    await broadcaster.publish(
        run_id,
        "run.completed",
        {
            "verdict": decision.verdict.value,
            "risk_score": decision.risk_score,
            "report_id": report.id,
            "narrative": {"status": "pending"},
            "reasons": report.reasons_json,
        },
        session=session,
    )

    # Narrative generation (offline template fallback handles timeout/no key)
    context = build_narrative_context(
        decision.verdict, decision.risk_score, decision.reasons, decision.findings
    )
    narrative_result = await generate_narrative(context, api_key=settings.openai_api_key)
    report = await complete_report_narrative(
        session, run_id=run_id, narrative_result=narrative_result
    )

    await broadcaster.publish(
        run_id,
        "report.narrative_ready",
        {
            "narrative": {
                "status": report.narrative_status.value,
                "text": report.narrative_text,
                "model": report.narrative_model,
            }
        },
        session=session,
    )

    await session.commit()

    return CreateRunResponse(
        run_id=run_id,
        mode="demo",
        status="completed",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=EXPECTED_STEPS,
    )
