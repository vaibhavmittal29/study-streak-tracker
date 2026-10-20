"""Endpoints for daily and weekly goal progress."""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import get_clock
from app.database import get_db
from app.schemas import GoalsProgressOut
from app.services.goals_service import compute_goal_progress

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("/progress", response_model=GoalsProgressOut)
def get_goal_progress(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> GoalsProgressOut:
    """Calculate and return progress against daily and weekly goals."""
    return compute_goal_progress(db, today)
