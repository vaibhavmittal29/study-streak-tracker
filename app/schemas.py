"""Pydantic schemas for request validation and response serialization."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SessionBase(BaseModel):
    """Base fields shared across session creation and responses."""

    subject: Annotated[
        str,
        Field(min_length=1, max_length=50, description="Name of subject studied"),
    ]
    duration_minutes: Annotated[
        int, Field(ge=1, le=1440, description="Study duration in minutes (1 to 1440)")
    ]
    date: Annotated[date, Field(description="Calendar date of study session")]
    notes: Annotated[str | None, Field(default=None, max_length=200, description="Optional notes")]

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        """Trim subject and ensure it is non-empty."""
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Subject cannot be empty or whitespace only")
        if len(cleaned) > 50:
            raise ValueError("Subject cannot exceed 50 characters")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        """Clean optional notes string."""
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None


class SessionCreate(SessionBase):
    """Payload for creating a new study session."""

    pass


class SessionUpdate(SessionBase):
    """Payload for updating an existing study session (full replacement)."""

    pass


class SessionOut(SessionBase):
    """Schema for returning session details to clients."""

    id: int
    subject_key: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionList(BaseModel):
    """Paginated list of study sessions."""

    items: list[SessionOut]
    total: int
    limit: int
    offset: int


class StreakOut(BaseModel):
    """Streak statistics, status flags, and freeze metrics."""

    current_streak: int
    longest_streak: int
    studied_today: bool
    streak_at_risk: bool
    last_study_date: date | None
    freeze_enabled: bool
    freeze_available_this_week: bool
    frozen_dates: list[date]
    today: date
    week_start: date


class SubjectStat(BaseModel):
    """Subject study summary."""

    subject: str
    minutes: int
    sessions: int


class WeeklyStatsOut(BaseModel):
    """Weekly study minutes grouped by subject for the active ISO week."""

    week_start: date
    week_end: date
    total_minutes: int
    subjects: list[SubjectStat]


class TimeSeriesPoint(BaseModel):
    """Single aggregated data point in time series."""

    date: str  # YYYY-MM-DD
    minutes: int
    sessions: int


class TimeSeriesOut(BaseModel):
    """Zero-filled time series for charts."""

    from_date: date
    to_date: date
    granularity: str
    points: list[TimeSeriesPoint]
    total_minutes: int


class SettingsBase(BaseModel):
    """Settings payload schema."""

    timezone: str = "Asia/Kolkata"
    freeze_enabled: bool = True
    daily_goal_minutes: int | None = None
    weekly_goal_minutes: int | None = None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Ensure timezone string is a recognized IANA timezone identifier."""
        import zoneinfo

        if v not in zoneinfo.available_timezones():
            raise ValueError(f"Invalid IANA timezone: '{v}'")
        return v

    @field_validator("daily_goal_minutes", "weekly_goal_minutes")
    @classmethod
    def validate_positive_goals(cls, v: int | None) -> int | None:
        """Goals must be positive integers or null."""
        if v is not None and v <= 0:
            raise ValueError("Goal minutes must be a positive integer greater than 0")
        return v


class SettingsOut(SettingsBase):
    """Settings response model."""

    model_config = ConfigDict(from_attributes=True)


class DailyGoalProgress(BaseModel):
    """Daily goal achievement breakdown."""

    goal_minutes: int
    done_minutes: int
    percent: float
    remaining: int
    met: bool


class WeeklyGoalProgress(BaseModel):
    """Weekly goal achievement breakdown."""

    goal_minutes: int
    done_minutes: int
    percent: float
    remaining: int
    met: bool
    days_left_including_today: int
    required_per_day: int


class GoalsProgressOut(BaseModel):
    """Progress towards daily and weekly study targets."""

    daily: DailyGoalProgress | None
    weekly: WeeklyGoalProgress | None
