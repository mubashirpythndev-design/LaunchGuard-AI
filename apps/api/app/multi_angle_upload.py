"""Validate and enroll a four-angle capture before starting background inspection."""

import asyncio
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from agent.multi_angle import run_multi_angle
from app.config import get_settings
from app.events import broadcaster
from app.schemas import CreateRunResponse
from cv.frameio import CorruptImageError, decode_image
from db.models import InspectionImageModel, RocketModel, RunMode, SourceType
from db.repo import create_run, init_checklist_steps
from rule_engine.types import QUADRANTS, Quadrant


async def create_multi_angle(
    rocket_id: str,
    uploads: dict[Quadrant, UploadFile | None],
    session: AsyncSession,
    background_tasks: BackgroundTasks,
) -> CreateRunResponse:
    if await session.get(RocketModel, rocket_id) is None:
        raise HTTPException(404, "Registered rocket profile not found.")
    if not any(uploads.values()):
        raise HTTPException(422, "Provide at least one quadrant image.")

    validated: dict[Quadrant, tuple[bytes, str, int, int]] = {}
    for quadrant, upload in uploads.items():
        if upload is None:
            continue
        mime = upload.content_type or ""
        if mime not in ("image/jpeg", "image/png", "image/webp"):
            raise HTTPException(415, f"{quadrant.title()}: use JPG, PNG, or WebP.")
        content = await upload.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(413, f"{quadrant.title()}: image exceeds 10 MB.")
        try:
            image = await asyncio.to_thread(decode_image, content)
        except CorruptImageError as exc:
            raise HTTPException(422, f"{quadrant.title()}: unreadable image.") from exc
        height, width = image.shape[:2]
        validated[quadrant] = (content, mime, width, height)

    run_id = str(uuid.uuid4())
    media_dir = Path(get_settings().media_root) / "runs" / run_id
    media_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    try:
        await create_run(
            session, RunMode.INSPECTION, SourceType.IMAGE_UPLOAD, run_id=run_id, rocket_id=rocket_id
        )
        for quadrant in QUADRANTS:
            values = validated.get(quadrant)
            record = InspectionImageModel(run_id=run_id, quadrant=quadrant)
            if values:
                content, mime, width, height = values
                path = media_dir / f"{quadrant}.image"
                paths.append(path)
                path.write_bytes(content)
                record.image_path = str(path)
                record.content_type = mime
                record.width = width
                record.height = height
            session.add(record)
        await init_checklist_steps(session, run_id)
        await broadcaster.publish(
            run_id,
            "run.started",
            {
                "run_id": run_id,
                "mode": "inspection",
                "source_type": "image_upload",
                "rocket_id": rocket_id,
            },
            session=session,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        for path in paths:
            path.unlink(missing_ok=True)
        media_dir.rmdir()
        raise
    background_tasks.add_task(run_multi_angle, run_id)
    return CreateRunResponse(
        run_id=run_id,
        mode="inspection",
        status="running",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=["body", "fins", "launchpad_area", "weather_manual", "decision"],
    )
