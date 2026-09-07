"""Excel export endpoints for journals, weekly summaries, and monthly rollups."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services import export_service

router = APIRouter(prefix="/export", tags=["export"])


def _xlsx_response(payload: bytes, filename: str) -> Response:
    # RFC 5987 filename* for non-ASCII safety; ASCII filename fallback for older clients.
    disposition = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=payload,
        media_type=export_service.XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": disposition},
    )


@router.get(
    "/journals",
    summary="Download journals as Excel",
    response_class=Response,
    responses={200: {"content": {export_service.XLSX_MEDIA_TYPE: {}}}},
)
def export_journals(
    date_from: date | None = Query(default=None, description="Inclusive start date"),
    date_to: date | None = Query(default=None, description="Inclusive end date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    payload, filename = export_service.export_journals(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
    )
    return _xlsx_response(payload, filename)


@router.get(
    "/weekly-summaries",
    summary="Download weekly summaries as Excel",
    response_class=Response,
    responses={200: {"content": {export_service.XLSX_MEDIA_TYPE: {}}}},
)
def export_weekly_summaries(
    date_from: date | None = Query(default=None, description="Inclusive start (overlaps weeks)"),
    date_to: date | None = Query(default=None, description="Inclusive end (overlaps weeks)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    payload, filename = export_service.export_weekly_summaries(
        db,
        current_user.id,
        date_from=date_from,
        date_to=date_to,
    )
    return _xlsx_response(payload, filename)


@router.get(
    "/monthly-summary",
    summary="Download a monthly summary Excel workbook",
    response_class=Response,
    responses={200: {"content": {export_service.XLSX_MEDIA_TYPE: {}}}},
)
def export_monthly_summary(
    year: int = Query(..., ge=1970, le=9999),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    payload, filename = export_service.export_monthly_summary(
        db,
        current_user.id,
        year=year,
        month=month,
    )
    return _xlsx_response(payload, filename)
