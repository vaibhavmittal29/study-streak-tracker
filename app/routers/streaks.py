"""Streak calculation endpoint reflecting current user streak state."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import get_clock, get_or_create_settings
from app.database import get_db
from app.models import StudySession
from app.schemas import StreakOut
from app.services.streak_engine import compute_streaks

router = APIRouter(prefix="/api/streak", tags=["streak"])


@router.get("", response_model=StreakOut)
def get_streak_metrics(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> StreakOut:
    """Compute and return current streak, longest streak, and freeze status.

    Recomputed from logged session dates dynamically on every request to guarantee
    that session edits or deletions can never leave stale streak counters.
    """
    settings = get_or_create_settings(db)

    # Fetch unique session dates up to today
    records = db.query(StudySession.date).distinct().all()
    study_dates = {row[0] for row in records}

    result = compute_streaks(
        study_dates=study_dates,
        today=today,
        freeze_enabled=settings.freeze_enabled,
    )

    week_start = today - timedelta(days=today.weekday())

    return StreakOut(
        current_streak=result.current,
        longest_streak=result.longest,
        studied_today=result.studied_today,
        streak_at_risk=result.at_risk,
        last_study_date=result.last_study_date,
        freeze_enabled=settings.freeze_enabled,
        freeze_available_this_week=result.freeze_available_this_week,
        frozen_dates=list(result.frozen_dates),
        today=today,
        week_start=week_start,
    )
