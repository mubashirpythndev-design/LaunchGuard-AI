"""Rocket profiles and golden reference baseline routes (specs/002-reference-inspection)."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    CreateRocketPayload,
    RocketListResponse,
    RocketReferenceItem,
    RocketResponse,
    UploadReferenceResponse,
)
from cv.frameio import CorruptImageError, decode_image
from cv.subject import locate_rocket
from db.base import get_db
from db.models import RocketModel
from db.repo import (
    count_rockets,
    create_rocket,
    delete_rocket,
    get_rocket,
    get_rocket_reference_by_quadrant,
    list_rockets,
    upsert_rocket_reference,
)

router = APIRouter(prefix="/api/rockets", tags=["rockets"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
VALID_QUADRANTS = {"front", "right", "back", "left"}
MIN_REFERENCE_WIDTH = 640
MIN_REFERENCE_HEIGHT = 480

REFERENCES_DIR = Path("data/references")


def _get_references_storage_dir() -> Path:
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    return REFERENCES_DIR


def _serialize_rocket_response(rocket: RocketModel) -> RocketResponse:
    ref_items = [
        RocketReferenceItem(
            id=ref.id,
            quadrant=ref.quadrant,
            image_url=f"/api/rockets/{rocket.id}/references/{ref.quadrant}",
            keypoint_count=ref.keypoint_count,
            created_at=ref.created_at.isoformat().replace("+00:00", "Z"),
        )
        for ref in (rocket.references or [])
    ]
    return RocketResponse(
        id=rocket.id,
        name=rocket.name,
        vehicle_class=rocket.vehicle_class,
        notes=rocket.notes,
        created_at=rocket.created_at.isoformat().replace("+00:00", "Z"),
        references=ref_items,
        reference_count=len(ref_items),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RocketResponse,
)
async def create_rocket_profile(
    payload: CreateRocketPayload,
    session: AsyncSession = Depends(get_db),
) -> RocketResponse:
    """Register a new rocket vehicle profile."""
    rocket = await create_rocket(
        session=session,
        name=payload.name.strip(),
        vehicle_class=payload.vehicle_class.strip(),
        notes=payload.notes.strip() if payload.notes else None,
    )
    await session.commit()
    # Reload with references relationship initialized
    reloaded = await get_rocket(session, rocket.id)
    assert reloaded is not None
    return _serialize_rocket_response(reloaded)


@router.get(
    "",
    response_model=RocketListResponse,
)
async def get_rockets_list(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> RocketListResponse:
    """Retrieve list of registered rocket profiles with baseline counts."""
    rockets = await list_rockets(session, limit=limit, offset=offset)
    total = await count_rockets(session)
    items = [_serialize_rocket_response(r) for r in rockets]
    return RocketListResponse(total=total, items=items)


@router.get(
    "/{rocket_id}",
    response_model=RocketResponse,
)
async def get_rocket_profile(
    rocket_id: str,
    session: AsyncSession = Depends(get_db),
) -> RocketResponse:
    """Retrieve details and reference images for a specific rocket profile."""
    rocket = await get_rocket(session, rocket_id)
    if not rocket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rocket profile '{rocket_id}' not found.",
        )
    return _serialize_rocket_response(rocket)


@router.delete(
    "/{rocket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Rocket profile deleted successfully."}
    },
)
async def delete_rocket_profile(
    rocket_id: str,
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a rocket profile and all cascaded golden reference records."""
    success = await delete_rocket(session, rocket_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rocket profile '{rocket_id}' not found.",
        )
    await session.commit()


@router.post(
    "/{rocket_id}/references/{quadrant}",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadReferenceResponse,
)
async def upload_golden_reference(
    rocket_id: str,
    quadrant: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> UploadReferenceResponse:
    """Upload or update a golden reference image for a specific quadrant."""
    normalized_quadrant = quadrant.lower().strip()
    if normalized_quadrant not in VALID_QUADRANTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid quadrant '{quadrant}'. Must be one of: {sorted(VALID_QUADRANTS)}.",
        )

    rocket = await get_rocket(session, rocket_id)
    if not rocket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rocket profile '{rocket_id}' not found.",
        )

    # Validate MIME type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{content_type}'. Must be JPEG, PNG, or WebP.",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Reference image exceeds 10 MB maximum limit.",
        )

    # Validate image decodability
    try:
        img_bgr = decode_image(contents)
    except CorruptImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    height, width = img_bgr.shape[:2]
    if width < MIN_REFERENCE_WIDTH or height < MIN_REFERENCE_HEIGHT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Reference image must be at least {MIN_REFERENCE_WIDTH}x"
                f"{MIN_REFERENCE_HEIGHT} pixels; received {width}x{height}."
            ),
        )

    if locate_rocket(img_bgr) is None:
        raise HTTPException(
            status_code=422,
            detail="Rocket-like geometry could not be verified. Use an upright, unobscured "
            "side view with the nose, body and both fins visible; documents and unsupported "
            "views cannot be enrolled as reference images.",
        )

    # Compute keypoints to assess baseline richness
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1500)  # type: ignore[attr-defined]
    keypoints = orb.detect(gray, None)
    keypoint_count = len(keypoints)

    # Save to storage directory
    storage_dir = _get_references_storage_dir()
    file_ext = Path(file.filename or "reference.jpg").suffix.lower()
    if file_ext not in (".jpg", ".jpeg", ".png", ".webp"):
        file_ext = ".jpg"
    target_path = storage_dir / f"{rocket_id}_{normalized_quadrant}{file_ext}"

    with open(target_path, "wb") as f:
        f.write(contents)

    ref_record = await upsert_rocket_reference(
        session=session,
        rocket_id=rocket_id,
        quadrant=normalized_quadrant,
        image_path=str(target_path),
        keypoint_count=keypoint_count,
    )
    await session.commit()

    return UploadReferenceResponse(
        id=ref_record.id,
        rocket_id=rocket_id,
        quadrant=normalized_quadrant,
        image_url=f"/api/rockets/{rocket_id}/references/{normalized_quadrant}",
        keypoint_count=keypoint_count,
    )


@router.get(
    "/{rocket_id}/references/{quadrant}",
    response_class=FileResponse,
    responses={
        status.HTTP_200_OK: {
            "content": {
                "image/jpeg": {},
                "image/png": {},
                "image/webp": {},
            },
            "description": "Binary golden reference image",
        }
    },
)
async def get_golden_reference_image(
    rocket_id: str,
    quadrant: str,
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Retrieve raw image file for a rocket quadrant reference."""
    normalized_quadrant = quadrant.lower().strip()
    ref = await get_rocket_reference_by_quadrant(session, rocket_id, normalized_quadrant)
    if not ref or not os.path.exists(ref.image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference image for rocket '{rocket_id}', quadrant '{quadrant}' not found.",
        )

    ext = Path(ref.image_path).suffix.lower()
    media_type = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
    return FileResponse(ref.image_path, media_type=media_type)
