"""Endpoints for exporting study data in standard formats."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.clock import get_clock
from app.database import get_db
from app.models import StudySession
from app.services.csv_export import generate_sessions_csv

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/export.csv")
def export_sessions_csv(
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> Response:
    """Download study sessions as a UTF-8 encoded CSV attachment."""
    query = db.query(StudySession)
    if from_date:
        query = query.filter(StudySession.date >= from_date)
    if to_date:
        query = query.filter(StudySession.date <= to_date)

    sessions = query.order_by(StudySession.date.asc(), StudySession.id.asc()).all()
    csv_text = generate_sessions_csv(sessions)

    filename = f"study_sessions_{today.isoformat()}.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "text/csv; charset=utf-8",
    }

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers=headers,
    )
