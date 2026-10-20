"""Endpoints for user settings, timezone, and study goals."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import get_or_create_settings
from app.database import get_db
from app.schemas import SettingsBase, SettingsOut

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)) -> SettingsOut:
    """Retrieve current user settings."""
    return get_or_create_settings(db)


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsBase, db: Session = Depends(get_db)) -> SettingsOut:
    """Update timezone, freeze toggle, and daily/weekly goals."""
    user_settings = get_or_create_settings(db)
    user_settings.timezone = payload.timezone
    user_settings.freeze_enabled = payload.freeze_enabled
    user_settings.daily_goal_minutes = payload.daily_goal_minutes
    user_settings.weekly_goal_minutes = payload.weekly_goal_minutes

    db.commit()
    db.refresh(user_settings)
    return user_settings
