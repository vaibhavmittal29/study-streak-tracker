"""Tests for Study Session CRUD API endpoints and validation rules."""

import tempfile
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import StudySession


def test_session_crud_lifecycle(client: TestClient, override_clock) -> None:
    """Verify full create, read, update, delete lifecycle of a study session."""
    today = date(2026, 10, 20)
    override_clock(today)

    # 1. Create session
    payload = {
        "subject": "  Algorithms and Data Structures  ",
        "duration_minutes": 90,
        "date": "2026-10-20",
        "notes": "Learned Red-Black Trees",
    }
    create_res = client.post("/api/sessions", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["id"] is not None
    # Verify subject was trimmed and subject_key lowercased
    assert created_data["subject"] == "Algorithms and Data Structures"
    assert created_data["subject_key"] == "algorithms and data structures"
    assert created_data["duration_minutes"] == 90
    assert created_data["date"] == "2026-10-20"
    session_id = created_data["id"]

    # 2. Read single session
    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == session_id

    # 3. Update session
    update_payload = {
        "subject": "Advanced Algorithms",
        "duration_minutes": 120,
        "date": "2026-10-20",
        "notes": "Mastered Graph traversals",
    }
    put_res = client.put(f"/api/sessions/{session_id}", json=update_payload)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["subject"] == "Advanced Algorithms"
    assert updated_data["duration_minutes"] == 120
    assert updated_data["notes"] == "Mastered Graph traversals"

    # 4. List sessions
    list_res = client.get("/api/sessions")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1
    assert list_data["items"][0]["id"] == session_id

    # 5. Delete session
    del_res = client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    # 6. Verify deleted
    get_again = client.get(f"/api/sessions/{session_id}")
    assert get_again.status_code == 404


def test_validation_empty_or_whitespace_subject(client: TestClient, override_clock) -> None:
    """Verify empty or whitespace-only subjects are rejected with 422."""
    override_clock(date(2026, 10, 20))
    res = client.post(
        "/api/sessions",
        json={"subject": "   ", "duration_minutes": 60, "date": "2026-10-20"},
    )
    assert res.status_code == 422


def test_validation_duration_boundaries(client: TestClient, override_clock) -> None:
    """Verify duration minutes must be between 1 and 1440."""
    override_clock(date(2026, 10, 20))
    # Test 0 minutes
    res_zero = client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 0, "date": "2026-10-20"},
    )
    assert res_zero.status_code == 422

    # Test 1441 minutes
    res_overflow = client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 1441, "date": "2026-10-20"},
    )
    assert res_overflow.status_code == 422


def test_validation_future_date_rejected(client: TestClient, override_clock) -> None:
    """Verify sessions dated in the future relative to user clock are rejected with 422."""
    today = date(2026, 10, 20)
    override_clock(today)

    future_res = client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 60, "date": "2026-10-21"},
    )
    assert future_res.status_code == 422
    assert "future" in future_res.json()["detail"].lower()


def test_validation_daily_cumulative_minutes_limit(client: TestClient, override_clock) -> None:
    """Verify cumulative study minutes for a single day cannot exceed 1440 minutes."""
    today = date(2026, 10, 20)
    override_clock(today)

    # Log 1400 minutes
    res1 = client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 1400, "date": "2026-10-20"},
    )
    assert res1.status_code == 201

    # Attempt logging 50 more minutes (1400 + 50 = 1450 > 1440) -> 422
    res2 = client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 50, "date": "2026-10-20"},
    )
    assert res2.status_code == 422
    assert "cannot exceed 1440 minutes" in res2.json()["detail"]


def test_validation_update_cumulative_minutes_limit(client: TestClient, override_clock) -> None:
    """Verify updating a session checks cumulative day limit excluding current session."""
    today = date(2026, 10, 20)
    override_clock(today)

    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 1000, "date": "2026-10-20"},
    )

    res2 = client.post(
        "/api/sessions",
        json={"subject": "OS", "duration_minutes": 400, "date": "2026-10-20"},
    )
    s2_id = res2.json()["id"]

    # Updating s2 to 440 (1000 + 440 = 1440) should succeed
    put_ok = client.put(
        f"/api/sessions/{s2_id}",
        json={"subject": "OS", "duration_minutes": 440, "date": "2026-10-20"},
    )
    assert put_ok.status_code == 200

    # Updating s2 to 450 (1000 + 450 = 1450 > 1440) should fail
    put_fail = client.put(
        f"/api/sessions/{s2_id}",
        json={"subject": "OS", "duration_minutes": 450, "date": "2026-10-20"},
    )
    assert put_fail.status_code == 422


def test_list_filters_and_deterministic_ordering(client: TestClient, override_clock) -> None:
    """Verify session filtering by date range, subject, and descending ordering."""
    override_clock(date(2026, 10, 20))

    # Log 3 sessions on different dates
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-18"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "Web Dev", "duration_minutes": 45, "date": "2026-10-19"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "dsa", "duration_minutes": 90, "date": "2026-10-20"},
    )

    # 1. Filter by subject (case-insensitive)
    dsa_res = client.get("/api/sessions?subject=DSA")
    assert dsa_res.status_code == 200
    dsa_items = dsa_res.json()["items"]
    assert len(dsa_items) == 2
    # Verify deterministic ordering: newest date first
    assert dsa_items[0]["date"] == "2026-10-20"
    assert dsa_items[1]["date"] == "2026-10-18"

    # 2. Filter by date range
    range_res = client.get("/api/sessions?from=2026-10-19&to=2026-10-20")
    assert range_res.status_code == 200
    assert len(range_res.json()["items"]) == 2

    # 3. Pagination limit and offset
    page_res = client.get("/api/sessions?limit=1&offset=1")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["total"] == 3
    assert len(page_data["items"]) == 1
    assert page_data["items"][0]["date"] == "2026-10-19"


def test_not_found_errors(client: TestClient) -> None:
    """Verify 404 response on non-existent IDs for GET, PUT, and DELETE."""
    assert client.get("/api/sessions/99999").status_code == 404
    assert client.delete("/api/sessions/99999").status_code == 404
    assert (
        client.put(
            "/api/sessions/99999",
            json={"subject": "Math", "duration_minutes": 60, "date": "2026-10-10"},
        ).status_code
        == 404
    )


def test_disk_persistence_across_connections() -> None:
    """Verify data persists when database connection/engine is closed and re-opened."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "persistent_test.db"
        sqlite_url = f"sqlite:///{db_path}"

        # 1. First connection: create tables and insert record
        engine_1 = create_engine(sqlite_url)
        Base.metadata.create_all(bind=engine_1)
        Session_1 = sessionmaker(bind=engine_1)
        with Session_1() as s1:
            s1.add(
                StudySession(
                    subject="Physics",
                    subject_key="physics",
                    duration_minutes=45,
                    date=date(2026, 10, 15),
                )
            )
            s1.commit()
        engine_1.dispose()

        # 2. Second completely new connection: read record
        engine_2 = create_engine(sqlite_url)
        Session_2 = sessionmaker(bind=engine_2)
        with Session_2() as s2:
            saved = s2.query(StudySession).filter(StudySession.subject == "Physics").first()
            assert saved is not None
            assert saved.duration_minutes == 45
            assert saved.date == date(2026, 10, 15)
        engine_2.dispose()
