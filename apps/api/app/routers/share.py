"""Public read-only report sharing API router (contracts/api.md, FR-033)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import MANDATED_DISCLAIMER
from app.schemas import (
    ActionSchema,
    ChecklistStepSchema,
    NarrativeSchema,
    PublicReportResponse,
    ReasonSchema,
)
from db.base import get_db
from db.repo import get_report_by_share_token, get_run
from rule_engine.types import Severity

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{token}", response_model=PublicReportResponse)
async def get_public_report(
    token: str,
    session: AsyncSession = Depends(get_db),
) -> PublicReportResponse:
    """Retrieve public read-only report by capability share token."""
    report = await get_report_by_share_token(session, token)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": {
                    "code": "SHARE_NOT_AVAILABLE",
                    "message": "Share link is no longer available or has expired.",
                }
            },
        )

    run = await get_run(session, report.run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": {
                    "code": "SHARE_NOT_AVAILABLE",
                    "message": "The run associated with this share link is no longer available.",
                }
            },
        )

    return PublicReportResponse(
        report_id=report.id,
        run_id=report.run_id,
        verdict=report.verdict,
        risk_score=report.risk_score,
        disclaimer=report.disclaimer or MANDATED_DISCLAIMER,
        checklist=[ChecklistStepSchema(**s) for s in report.checklist_json],
        reasons=[
            ReasonSchema(**r)
            if isinstance(r, dict)
            else ReasonSchema(
                check_id="generic",
                severity=Severity.WARNING,
                message=str(r),
                confidence=1.0,
            )
            for r in (report.reasons_json or [])
        ],
        recommended_actions=[
            ActionSchema(**a)
            if isinstance(a, dict)
            else ActionSchema(check_id="generic", action=str(a))
            for a in (report.recommended_actions_json or [])
        ],
        narrative=NarrativeSchema(
            status=report.narrative_status.value,
            text=report.narrative_text,
            model=report.narrative_model,
        ),
        annotated_image_url=report.annotated_ref,
        generated_at=report.generated_at.isoformat().replace("+00:00", "Z"),
    )
