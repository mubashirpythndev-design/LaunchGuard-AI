"""Persisted per-angle media exposed through the generated API contract."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import QuadrantImageSchema
from db.models import InspectionImageModel, RocketReferenceModel, RunModel
from rule_engine.types import QUADRANTS


async def quadrant_images(session: AsyncSession, run_id: str) -> list[QuadrantImageSchema]:
    records = (
        await session.scalars(
            select(InspectionImageModel).where(InspectionImageModel.run_id == run_id)
        )
    ).all()
    by_angle = {record.quadrant: record for record in records}
    run = await session.get(RunModel, run_id)
    reference_quadrants: set[str] = set()
    if run and run.rocket_id:
        reference_quadrants = set(
            (
                await session.scalars(
                    select(RocketReferenceModel.quadrant).where(
                        RocketReferenceModel.rocket_id == run.rocket_id
                    )
                )
            ).all()
        )
    return [
        QuadrantImageSchema(
            quadrant=angle,
            width=by_angle[angle].width,
            height=by_angle[angle].height,
            image_url=f"/api/runs/{run_id}/quadrants/{angle}/image"
            if by_angle[angle].image_path
            else None,
            annotated_image_url=f"/api/runs/{run_id}/quadrants/{angle}/annotated"
            if by_angle[angle].image_path
            and Path(by_angle[angle].image_path or "").with_suffix(".annotated.jpg").is_file()
            else None,
            reference_image_url=f"/api/rockets/{run.rocket_id}/references/{angle}"
            if run and run.rocket_id and angle in reference_quadrants
            else None,
            aligned_image_url=f"/api/runs/{run_id}/quadrants/{angle}/aligned"
            if by_angle[angle].image_path
            and Path(by_angle[angle].image_path or "").with_suffix(".aligned.jpg").is_file()
            else None,
            heatmap_image_url=f"/api/runs/{run_id}/quadrants/{angle}/heatmap"
            if by_angle[angle].image_path
            and Path(by_angle[angle].image_path or "").with_suffix(".heatmap.jpg").is_file()
            else None,
        )
        for angle in QUADRANTS
        if angle in by_angle
    ]
