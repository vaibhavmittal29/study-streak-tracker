"""Service calculating daily and weekly study goal progress."""

import math
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.clock import get_or_create_settings
from app.models import StudySession
from app.schemas import DailyGoalProgress, GoalsProgressOut, WeeklyGoalProgress


def compute_goal_progress(db: Session, today: date) -> GoalsProgressOut:
    """Calculate progress against daily and weekly study duration goals."""
    settings = get_or_create_settings(db)

    daily_progress: DailyGoalProgress | None = None
    if settings.daily_goal_minutes is not None:
        daily_done = (
            db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0))
            .filter(StudySession.date == today)
            .scalar()
        )
        daily_goal = settings.daily_goal_minutes
        daily_percent = round((daily_done / daily_goal) * 100, 1)
        daily_remaining = max(0, daily_goal - daily_done)
        daily_progress = DailyGoalProgress(
            goal_minutes=daily_goal,
            done_minutes=daily_done,
            percent=daily_percent,
            remaining=daily_remaining,
            met=daily_done >= daily_goal,
        )

    weekly_progress: WeeklyGoalProgress | None = None
    if settings.weekly_goal_minutes is not None:
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        weekly_done = (
            db.query(func.coalesce(func.sum(StudySession.duration_minutes), 0))
            .filter(StudySession.date >= week_start, StudySession.date <= week_end)
            .scalar()
        )
        weekly_goal = settings.weekly_goal_minutes
        weekly_percent = round((weekly_done / weekly_goal) * 100, 1)
        weekly_remaining = max(0, weekly_goal - weekly_done)
        days_left_including_today = 7 - today.weekday()
        required_per_day = (
            math.ceil(weekly_remaining / days_left_including_today) if weekly_remaining > 0 else 0
        )
        weekly_progress = WeeklyGoalProgress(
            goal_minutes=weekly_goal,
            done_minutes=weekly_done,
            percent=weekly_percent,
            remaining=weekly_remaining,
            met=weekly_done >= weekly_goal,
            days_left_including_today=days_left_including_today,
            required_per_day=required_per_day,
        )

    return GoalsProgressOut(
        daily=daily_progress,
        weekly=weekly_progress,
    )
