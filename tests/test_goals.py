"""Unit and integration tests for user settings and goal progress tracking."""

from datetime import date

from fastapi.testclient import TestClient


def test_settings_get_and_update(client: TestClient) -> None:
    """Verify settings fetch, defaults, and valid updates."""
    # 1. Fetch defaults
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    defaults = get_res.json()
    assert defaults["timezone"] == "Asia/Kolkata"
    assert defaults["freeze_enabled"] is True
    assert defaults["daily_goal_minutes"] is None
    assert defaults["weekly_goal_minutes"] is None

    # 2. Update settings
    payload = {
        "timezone": "UTC",
        "freeze_enabled": False,
        "daily_goal_minutes": 90,
        "weekly_goal_minutes": 600,
    }
    put_res = client.put("/api/settings", json=payload)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["timezone"] == "UTC"
    assert updated["freeze_enabled"] is False
    assert updated["daily_goal_minutes"] == 90
    assert updated["weekly_goal_minutes"] == 600


def test_settings_validation_errors(client: TestClient) -> None:
    """Verify 422 on invalid IANA timezone and non-positive goals."""
    # Invalid timezone
    res_tz = client.put(
        "/api/settings",
        json={"timezone": "Invalid/Fake_Zone", "freeze_enabled": True},
    )
    assert res_tz.status_code == 422

    # Non-positive daily goal
    res_goal = client.put(
        "/api/settings",
        json={"timezone": "UTC", "freeze_enabled": True, "daily_goal_minutes": 0},
    )
    assert res_goal.status_code == 422


def test_goal_progress_null_when_unset(client: TestClient, override_clock) -> None:
    """Verify goal progress returns null when goals are not configured."""
    override_clock(date(2026, 10, 20))
    # Ensure goals are null
    client.put(
        "/api/settings",
        json={"timezone": "Asia/Kolkata", "freeze_enabled": True, "daily_goal_minutes": None},
    )

    res = client.get("/api/goals/progress")
    assert res.status_code == 200
    data = res.json()
    assert data["daily"] is None
    assert data["weekly"] is None


def test_goal_progress_calculation(client: TestClient, override_clock) -> None:
    """Verify daily and weekly goal progress calculations, remaining, and required_per_day."""
    # 2026-10-20 is Tuesday (weekday 1)
    # Week start: Mon Oct 19. Days left including today (Tue..Sun): 7 - 1 = 6 days.
    today = date(2026, 10, 20)
    override_clock(today)

    # Set daily goal = 90 mins, weekly goal = 600 mins
    client.put(
        "/api/settings",
        json={
            "timezone": "Asia/Kolkata",
            "freeze_enabled": True,
            "daily_goal_minutes": 90,
            "weekly_goal_minutes": 600,
        },
    )

    # Log 60 mins yesterday (Oct 19) and 60 mins today (Oct 20)
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-19"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 60, "date": "2026-10-20"},
    )

    res = client.get("/api/goals/progress")
    assert res.status_code == 200
    data = res.json()

    # Daily: done 60 of 90 -> 66.7%, remaining 30, met False
    daily = data["daily"]
    assert daily is not None
    assert daily["goal_minutes"] == 90
    assert daily["done_minutes"] == 60
    assert daily["percent"] == 66.7
    assert daily["remaining"] == 30
    assert daily["met"] is False

    # Weekly: done 120 of 600 -> 20.0%, remaining 480, days left 6,
    # required_per_day = ceil(480/6) = 80
    weekly = data["weekly"]
    assert weekly is not None
    assert weekly["goal_minutes"] == 600
    assert weekly["done_minutes"] == 120
    assert weekly["percent"] == 20.0
    assert weekly["remaining"] == 480
    assert weekly["days_left_including_today"] == 6
    assert weekly["required_per_day"] == 80
    assert weekly["met"] is False


def test_goal_met_status(client: TestClient, override_clock) -> None:
    """Verify goal met flag when done minutes reach or exceed target."""
    today = date(2026, 10, 20)
    override_clock(today)

    client.put(
        "/api/settings",
        json={
            "timezone": "Asia/Kolkata",
            "freeze_enabled": True,
            "daily_goal_minutes": 60,
            "weekly_goal_minutes": 60,
        },
    )
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 75, "date": "2026-10-20"},
    )

    res = client.get("/api/goals/progress")
    data = res.json()
    assert data["daily"]["met"] is True
    assert data["daily"]["remaining"] == 0
    assert data["weekly"]["met"] is True
    assert data["weekly"]["remaining"] == 0
    assert data["weekly"]["required_per_day"] == 0
