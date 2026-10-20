"""Integration tests for the /api/streak endpoint, dynamic recomputation, and edge cases."""

from datetime import date

from fastapi.testclient import TestClient


def test_api_streak_basic_flow(client: TestClient, override_clock) -> None:
    """Verify /api/streak returns correct streak counts and status flags."""
    today = date(2026, 10, 20)
    override_clock(today)

    # Initially 0 streak
    res = client.get("/api/streak")
    assert res.status_code == 200
    data = res.json()
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 0
    assert data["studied_today"] is False
    assert data["streak_at_risk"] is False
    assert data["week_start"] == "2026-10-19"  # Monday of this week

    # Log study today
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-20"},
    )
    res_after = client.get("/api/streak")
    assert res_after.status_code == 200
    after_data = res_after.json()
    assert after_data["current_streak"] == 1
    assert after_data["longest_streak"] == 1
    assert after_data["studied_today"] is True
    assert after_data["streak_at_risk"] is False
    assert after_data["last_study_date"] == "2026-10-20"


def test_e17_edit_session_date_recomputes_streak(client: TestClient, override_clock) -> None:
    """E17: Editing a session date immediately updates the computed streak."""
    today = date(2026, 10, 20)
    override_clock(today)

    # Create session on Oct 18
    res = client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-18"},
    )
    session_id = res.json()["id"]

    # Oct 18 was 2 days ago; with freeze, Oct 19 is frozen, current = 1
    streak_res1 = client.get("/api/streak")
    assert streak_res1.json()["current_streak"] == 1

    # Edit date to Oct 20 (today)
    client.put(
        f"/api/sessions/{session_id}",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-20"},
    )

    streak_res2 = client.get("/api/streak")
    data2 = streak_res2.json()
    assert data2["current_streak"] == 1
    assert data2["studied_today"] is True
    assert data2["frozen_dates"] == []


def test_e18_delete_only_session_of_day_breaks_streak(client: TestClient, override_clock) -> None:
    """E18: Deleting the only session on a critical day updates streak immediately."""
    today = date(2026, 10, 20)
    override_clock(today)

    # Create session on Oct 19 and Oct 20
    s1 = client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 60, "date": "2026-10-19"},
    ).json()["id"]
    client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 60, "date": "2026-10-20"},
    )

    streak_2 = client.get("/api/streak").json()
    assert streak_2["current_streak"] == 2

    # Delete Oct 19 session
    del_res = client.delete(f"/api/sessions/{s1}")
    assert del_res.status_code == 204

    # Streak should immediately reflect only 1 day (today)
    streak_1 = client.get("/api/streak").json()
    assert streak_1["current_streak"] == 1


def test_e15_midnight_boundary_transition(client: TestClient, override_clock) -> None:
    """E15: At 23:59:59 today is pending; at 00:00:00 it becomes completed yesterday."""
    # Day D = 2026-10-19 (Mon), user studied
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-19"},
    )

    # At 23:59:59 on Day D+1 (2026-10-20, Tue), user hasn't studied yet:
    # Today is pending, streak is alive at 1 (from Mon), at_risk is True.
    override_clock(date(2026, 10, 20))
    res_tue = client.get("/api/streak").json()
    assert res_tue["current_streak"] == 1
    assert res_tue["studied_today"] is False
    assert res_tue["streak_at_risk"] is True

    # At 00:00:00 on Day D+2 (2026-10-21, Wed), Tue is now a completed missed day:
    # Tue consumes the ISO week freeze, so streak survives at 1, but freeze is used!
    override_clock(date(2026, 10, 21))
    res_wed = client.get("/api/streak").json()
    assert res_wed["current_streak"] == 1
    assert res_wed["studied_today"] is False
    assert res_wed["frozen_dates"] == ["2026-10-20"]
    assert res_wed["freeze_available_this_week"] is False

    # At 00:00:00 on Day D+3 (2026-10-22, Thu), Wed is now also a completed missed day:
    # Second miss in the same week -> streak breaks to 0!
    override_clock(date(2026, 10, 22))
    res_thu = client.get("/api/streak").json()
    assert res_thu["current_streak"] == 0
    assert res_thu["streak_at_risk"] is False


def test_e16_timezone_shift_near_midnight(client: TestClient, override_clock) -> None:
    """E16: Timezone change shifts 'today' calendar date without modifying stored dates."""
    # Stored session is on 2026-10-20
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-20"},
    )

    # When user is in a timezone where today is 2026-10-20:
    override_clock(date(2026, 10, 20))
    r1 = client.get("/api/streak").json()
    assert r1["studied_today"] is True
    assert r1["current_streak"] == 1

    # When user timezone shifts ahead so today is 2026-10-21:
    override_clock(date(2026, 10, 21))
    r2 = client.get("/api/streak").json()
    # 2026-10-20 is now yesterday; today is pending
    assert r2["studied_today"] is False
    assert r2["current_streak"] == 1
    assert r2["streak_at_risk"] is True
