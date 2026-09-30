"""Demo mode scenarios API router (Constitution 6.I, contracts/api.md)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    CreateRunResponse,
    DemoScenarioItem,
    DemoScenariosResponse,
)
from db.base import get_db
from db.repo import get_demo_scenario, list_demo_scenarios

router = APIRouter(prefix="/api/demo", tags=["demo"])


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
    """Launch a pipeline run using bundled scenario data."""
    scenario = await get_demo_scenario(session, key)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demo scenario '{key}' not found.",
        )

    run_id = str(uuid.uuid4())
    return CreateRunResponse(
        run_id=run_id,
        mode="demo",
        status="running",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=["body", "fins", "launchpad_area", "weather_manual", "decision"],
    )
