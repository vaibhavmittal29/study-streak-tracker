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
