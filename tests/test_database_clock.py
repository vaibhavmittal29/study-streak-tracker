"""Unit tests for database session lifecycle, settings initialization, and injectable clock."""

from datetime import date

from sqlalchemy.orm import Session

from app.clock import get_clock, get_or_create_settings, get_today
from app.main import app
from app.models import Settings


def test_get_or_create_settings_is_idempotent(db_session: Session) -> None:
    """Verify settings row is created once with defaults and reused on subsequent calls."""
    settings_1 = get_or_create_settings(db_session)
    assert settings_1.id == 1
    assert settings_1.timezone == "Asia/Kolkata"
    assert settings_1.freeze_enabled is True

    # Call second time
    settings_2 = get_or_create_settings(db_session)
    assert settings_2.id == settings_1.id
    assert settings_2.timezone == settings_1.timezone

    # Only 1 record should exist
    assert db_session.query(Settings).count() == 1


def test_get_today_respects_timezone() -> None:
    """Verify get_today calculates a valid calendar date for a valid timezone."""
    today_kolkata = get_today("Asia/Kolkata")
    today_utc = get_today("UTC")
    assert isinstance(today_kolkata, date)
    assert isinstance(today_utc, date)


def test_clock_override_fixture(client, override_clock) -> None:
    """Verify that override_clock correctly alters the get_clock dependency."""
    fixed = date(2026, 1, 15)
    override_clock(fixed)
    resolved_today = app.dependency_overrides[get_clock]()
    assert resolved_today == fixed
