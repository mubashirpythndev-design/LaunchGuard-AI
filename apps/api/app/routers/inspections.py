"""Pre-launch inspection API routes (contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas import CreateRunResponse

router = APIRouter(prefix="/api/inspections", tags=["inspections"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateRunResponse,
)
async def create_inspection(
    file: UploadFile = File(...),
) -> CreateRunResponse:
    """Initiate a pre-launch inspection run from an uploaded rocket image."""
    content_type = file.content_type or ""
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPG, PNG, and WebP images are accepted.",
        )

    # Placeholder run ID generated for contract and route definition
    import uuid

    run_id = str(uuid.uuid4())
    return CreateRunResponse(
        run_id=run_id,
        mode="inspection",
        status="running",
        stream_url=f"/api/runs/{run_id}/stream",
        expected_steps=["body", "fins", "launchpad_area", "weather_manual", "decision"],
    )
