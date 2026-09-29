import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    model_configured: bool = False
    workers: int = 1


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    has_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    return HealthResponse(
        status="ok",
        version="0.1.0",
        model_configured=has_key,
        workers=1,
    )
