"""Injectable clock and timezone utilities.

Enforces zero direct calls to date.today() or datetime.now() across business
logic, ensuring all date calculations respect user timezone and can be
deterministically simulated in tests.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Settings


def get_or_create_settings(db: Session) -> Settings:
    """Retrieve the single settings row, creating it with defaults if absent."""
    user_settings = db.query(Settings).filter(Settings.id == 1).first()
    if not user_settings:
        user_settings = Settings(id=1, timezone="Asia/Kolkata", freeze_enabled=True)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
    return user_settings


def get_now(tz_name: str = "Asia/Kolkata") -> datetime:
    """Return the current datetime in the specified timezone."""
    return datetime.now(ZoneInfo(tz_name))


def get_today(tz_name: str = "Asia/Kolkata") -> date:
    """Return the current calendar date in the specified timezone."""
    return get_now(tz_name).date()


def get_clock(db: Session = Depends(get_db)) -> date:
    """FastAPI dependency resolving 'today' in the user's configured timezone.

    Can be cleanly overridden in test suites via `app.dependency_overrides[get_clock]`.
    """
    user_settings = get_or_create_settings(db)
    return get_today(user_settings.timezone)
