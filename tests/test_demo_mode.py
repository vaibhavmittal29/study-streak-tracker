"""Tests for demo mode functionality, auto-seeding, reset endpoint, and flood limits."""

from datetime import date

from fastapi.testclient import TestClient

from app.config import settings
from app.models import StudySession
from app.services.demo_seeder import seed_demo_data


def test_demo_mode_disabled_by_default(client: TestClient) -> None:
    """Verify demo mode is disabled by default and reset endpoint returns 404."""
    assert settings.DEMO_MODE is False

    status_res = client.get("/api/demo/status")
    assert status_res.status_code == 200
    assert status_res.json()["demo_mode"] is False

    reset_res = client.post("/api/demo/reset")
    assert reset_res.status_code == 404
    assert "Demo mode is disabled" in reset_res.json()["detail"]


def test_seed_demo_data_idempotency_and_relative_clock(db_session, override_clock) -> None:
    """Verify seed_demo_data produces a rich state ending yesterday relative to the clock."""
    test_today = date(2026, 10, 20)
    override_clock(test_today)

    # First seeding
    c1 = seed_demo_data(db_session, today=test_today, reset=False)
    assert c1 > 50

    # Second seeding without reset is a no-op (idempotent)
    c2 = seed_demo_data(db_session, today=test_today, reset=False)
    assert c2 == c1

    # Verify no session exists for today
    today_sessions = (
        db_session.query(StudySession).filter(StudySession.date == test_today).count()
    )
    assert today_sessions == 0


def test_demo_mode_active_behavior(client: TestClient, monkeypatch, override_clock) -> None:
    """Verify reset endpoint and dashboard metrics when DEMO_MODE is on."""
    test_today = date(2026, 10, 20)
    override_clock(test_today)

    # Enable DEMO_MODE for this test
    monkeypatch.setattr(settings, "DEMO_MODE", True)

    # Call reset endpoint
    reset_res = client.post("/api/demo/reset")
    assert reset_res.status_code == 200
    data = reset_res.json()
    assert data["status"] == "ok"
    assert data["sessions_count"] > 50

    # Verify /api/streak reflects rich demo state:
    # 1. studied_today is False
    # 2. streak_at_risk is True
    # 3. current_streak > 0 (alive from yesterday)
    # 4. longest_streak > current_streak
    streak_res = client.get("/api/streak")
    assert streak_res.status_code == 200
    streak_data = streak_res.json()
    assert streak_data["studied_today"] is False
    assert streak_data["streak_at_risk"] is True
    assert streak_data["current_streak"] >= 3
    assert streak_data["longest_streak"] > streak_data["current_streak"]


def test_demo_mode_max_sessions_cap(client: TestClient, monkeypatch, override_clock) -> None:
    """Verify demo mode returns 429 when DEMO_MAX_SESSIONS cap is reached."""
    override_clock(date(2026, 10, 20))

    monkeypatch.setattr(settings, "DEMO_MODE", True)
    # Set artificial cap to 2 sessions
    monkeypatch.setattr(settings, "DEMO_MAX_SESSIONS", 2)

    # Create 2 sessions (within cap)
    s1 = client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 30, "date": "2026-10-18"},
    )
    assert s1.status_code == 201

    s2 = client.post(
        "/api/sessions",
        json={"subject": "OS", "duration_minutes": 30, "date": "2026-10-19"},
    )
    assert s2.status_code == 201

    # 3rd session exceeds cap -> 429
    s3 = client.post(
        "/api/sessions",
        json={"subject": "CN", "duration_minutes": 30, "date": "2026-10-20"},
    )
    assert s3.status_code == 429
    assert "limit reached" in s3.json()["detail"].lower()
