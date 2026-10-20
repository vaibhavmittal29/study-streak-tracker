"""SQLAlchemy ORM models for Study Sessions and Settings."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    """Return current UTC timestamp without timezone offset issues."""
    return datetime.now(timezone.utc)


class StudySession(Base):
    """Represents an individual logged study session."""

    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class Settings(Base):
    """User preferences, timezone, goal settings, and streak configuration.

    Designed as a single-row configuration table (id=1).
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    freeze_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    daily_goal_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_goal_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
