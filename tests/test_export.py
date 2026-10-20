"""Tests for CSV export generation, filtering, formatting, and injection mitigation."""

import csv
import io
from datetime import date

from fastapi.testclient import TestClient


def test_export_empty_returns_header_only(client: TestClient, override_clock) -> None:
    """Verify empty database returns CSV with only the header row."""
    today = date(2026, 10, 20)
    override_clock(today)

    res = client.get("/api/export.csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert (
        'attachment; filename="study_sessions_2026-10-20.csv"' in res.headers["content-disposition"]
    )

    reader = list(csv.reader(io.StringIO(res.text)))
    assert len(reader) == 1
    assert reader[0] == ["id", "date", "subject", "duration_minutes", "notes", "created_at"]


def test_export_data_and_injection_guard(client: TestClient, override_clock) -> None:
    """Verify CSV rows, special characters (commas, quotes), and injection mitigation."""
    today = date(2026, 10, 20)
    override_clock(today)

    # 1. Normal session
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-18"},
    )
    # 2. Session with commas, quotes, and special characters in subject and notes
    client.post(
        "/api/sessions",
        json={
            "subject": 'Database "Systems", SQL',
            "duration_minutes": 90,
            "date": "2026-10-19",
            "notes": "Chapter 1, 2; 'important'",
        },
    )
    # 3. Potentially malicious formula payloads starting with =, +, -, @
    client.post(
        "/api/sessions",
        json={
            "subject": "=cmd|' /C calc'!A0",
            "duration_minutes": 45,
            "date": "2026-10-20",
            "notes": "+SUM(A1:A10)",
        },
    )

    res = client.get("/api/export.csv")
    assert res.status_code == 200

    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) == 4  # Header + 3 sessions

    # Check header
    assert rows[0] == ["id", "date", "subject", "duration_minutes", "notes", "created_at"]

    # Check row 2 (escaped quotes and commas)
    r2 = rows[2]
    assert r2[1] == "2026-10-19"
    assert r2[2] == 'Database "Systems", SQL'
    assert r2[3] == "90"
    assert r2[4] == "Chapter 1, 2; 'important'"

    # Check row 3 (injection mitigation prefixed with single quote)
    r3 = rows[3]
    assert r3[1] == "2026-10-20"
    assert r3[2] == "'=cmd|' /C calc'!A0"
    assert r3[4] == "'+SUM(A1:A10)"


def test_export_date_range_filtering(client: TestClient, override_clock) -> None:
    """Verify CSV export respects from and to query parameters."""
    override_clock(date(2026, 10, 20))

    client.post(
        "/api/sessions",
        json={"subject": "S1", "duration_minutes": 30, "date": "2026-10-15"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "S2", "duration_minutes": 30, "date": "2026-10-18"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "S3", "duration_minutes": 30, "date": "2026-10-20"},
    )

    res = client.get("/api/export.csv?from=2026-10-17&to=2026-10-19")
    assert res.status_code == 200

    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) == 2  # Header + S2
    assert rows[1][1] == "2026-10-18"
    assert rows[1][2] == "S2"
