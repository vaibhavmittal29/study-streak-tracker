"""Endpoints for logging, listing, updating, and deleting study sessions."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.clock import get_clock
from app.config import settings
from app.database import get_db
from app.models import StudySession
from app.schemas import SessionCreate, SessionList, SessionOut, SessionUpdate

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> StudySession:
    """Log a new study session with calendar validation."""
    # Enforce demo capacity cap if operating in demo mode
    if settings.DEMO_MODE:
        total_sessions = db.query(func.count(StudySession.id)).scalar()
        if total_sessions >= settings.DEMO_MAX_SESSIONS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Demo instance session limit reached ({settings.DEMO_MAX_SESSIONS} max). "
                    "Please reset demo data or delete old sessions."
                ),
            )

    if payload.date > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Session date cannot be in the future (today is {today})",
        )

    # Validate that cumulative minutes for this date do not exceed 24 hours (1440 minutes)
    existing_minutes = (
        db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .filter(StudySession.date == payload.date)
        .scalar()
    )
    if existing_minutes + payload.duration_minutes > 1440:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Total study time for {payload.date} cannot exceed 1440 minutes. "
                f"Already logged: {existing_minutes}m, attempted: {payload.duration_minutes}m."
            ),
        )

    new_session = StudySession(
        subject=payload.subject,
        subject_key=payload.subject.lower(),
        duration_minutes=payload.duration_minutes,
        date=payload.date,
        notes=payload.notes,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


@router.get("", response_model=SessionList)
def list_sessions(
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    subject: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> dict:
    """Retrieve filtered, paginated study sessions ordered newest date first."""
    query = db.query(StudySession)

    if from_date:
        query = query.filter(StudySession.date >= from_date)
    if to_date:
        query = query.filter(StudySession.date <= to_date)
    if subject:
        query = query.filter(StudySession.subject_key == subject.strip().lower())

    total = query.count()
    items = (
        query.order_by(StudySession.date.desc(), StudySession.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)) -> StudySession:
    """Retrieve a single study session by primary key ID."""
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study session with id {session_id} not found",
        )
    return session


@router.put("/{session_id}", response_model=SessionOut)
def update_session(
    session_id: int,
    payload: SessionUpdate,
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> StudySession:
    """Full update of an existing study session."""
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study session with id {session_id} not found",
        )

    if payload.date > today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Session date cannot be in the future (today is {today})",
        )

    # Check total for this date excluding this session
    existing_minutes = (
        db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0))
        .filter(StudySession.date == payload.date, StudySession.id != session_id)
        .scalar()
    )
    if existing_minutes + payload.duration_minutes > 1440:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Total study time for {payload.date} cannot exceed 1440 minutes. "
                f"Others: {existing_minutes}m, attempted: {payload.duration_minutes}m."
            ),
        )

    session.subject = payload.subject
    session.subject_key = payload.subject.lower()
    session.duration_minutes = payload.duration_minutes
    session.date = payload.date
    session.notes = payload.notes

    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a study session by ID."""
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study session with id {session_id} not found",
        )
    db.delete(session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
