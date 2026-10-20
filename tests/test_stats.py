"""Unit and integration tests for weekly statistics and zero-filled time series."""

from datetime import date

from fastapi.testclient import TestClient


def test_weekly_stats_empty(client: TestClient, override_clock) -> None:
    """Verify empty week returns 0 total minutes and empty subjects list."""
    today = date(2026, 10, 20)
    override_clock(today)

    res = client.get("/api/stats/weekly")
    assert res.status_code == 200
    data = res.json()
    assert data["total_minutes"] == 0
    assert data["subjects"] == []
    assert data["week_start"] == "2026-10-19"
    assert data["week_end"] == "2026-10-25"


def test_weekly_stats_case_insensitive_grouping_and_latest_spelling(
    client: TestClient, override_clock
) -> None:
    """Verify subjects are grouped case-insensitively and latest spelling is preserved."""
    today = date(2026, 10, 21)
    override_clock(today)

    # 1. Log "dsa" on Monday Oct 19
    client.post(
        "/api/sessions",
        json={"subject": "dsa", "duration_minutes": 60, "date": "2026-10-19"},
    )
    # 2. Log "DSA" on Wednesday Oct 21 (latest spelling)
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 90, "date": "2026-10-21"},
    )
    # 3. Log "Math" on Tuesday Oct 20
    client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 45, "date": "2026-10-20"},
    )

    res = client.get("/api/stats/weekly")
    assert res.status_code == 200
    data = res.json()
    assert data["total_minutes"] == 195
    assert len(data["subjects"]) == 2

    dsa_stat = next(s for s in data["subjects"] if s["subject"].lower() == "dsa")
    assert dsa_stat["subject"] == "DSA"  # Preserved most recent spelling
    assert dsa_stat["minutes"] == 150
    assert dsa_stat["sessions"] == 2

    # Verify descending sort order by minutes
    assert data["subjects"][0]["minutes"] >= data["subjects"][1]["minutes"]


def test_weekly_stats_iso_week_boundary(client: TestClient, override_clock) -> None:
    """Verify Sunday belongs to previous week and Monday starts a new week."""
    # Sunday Oct 18 (Week 42) vs Monday Oct 19 (Week 43)
    override_clock(date(2026, 10, 19))

    client.post(
        "/api/sessions",
        json={"subject": "Physics", "duration_minutes": 100, "date": "2026-10-18"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "Chemistry", "duration_minutes": 50, "date": "2026-10-19"},
    )

    res = client.get("/api/stats/weekly")
    data = res.json()
    # Only Monday's session should be present in current week
    assert data["total_minutes"] == 50
    assert len(data["subjects"]) == 1
    assert data["subjects"][0]["subject"] == "Chemistry"


def test_timeseries_zero_filling_day_granularity(client: TestClient, override_clock) -> None:
    """Verify daily timeseries includes all dates in range with 0 for unstudied days."""
    today = date(2026, 10, 20)
    override_clock(today)

    # Log session only on Oct 19
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-19"},
    )

    # Request range from Oct 18 to Oct 20 (3 days)
    res = client.get("/api/stats/timeseries?from=2026-10-18&to=2026-10-20&granularity=day")
    assert res.status_code == 200
    data = res.json()
    assert data["total_minutes"] == 60
    assert len(data["points"]) == 3

    p0, p1, p2 = data["points"]
    assert p0["date"] == "2026-10-18" and p0["minutes"] == 0
    assert p1["date"] == "2026-10-19" and p1["minutes"] == 60
    assert p2["date"] == "2026-10-20" and p2["minutes"] == 0


def test_timeseries_week_granularity(client: TestClient, override_clock) -> None:
    """Verify weekly timeseries buckets by Monday date."""
    today = date(2026, 10, 20)
    override_clock(today)

    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 90, "date": "2026-10-19"},
    )

    res = client.get("/api/stats/timeseries?from=2026-10-12&to=2026-10-25&granularity=week")
    assert res.status_code == 200
    points = res.json()["points"]
    # Two weeks: Oct 12 (0 mins) and Oct 19 (90 mins)
    assert len(points) == 2
    assert points[0]["date"] == "2026-10-12" and points[0]["minutes"] == 0
    assert points[1]["date"] == "2026-10-19" and points[1]["minutes"] == 90


def test_timeseries_validation_errors(client: TestClient) -> None:
    """Verify 422 when from > to or range > 366 days."""
    # From > To
    res_inv = client.get("/api/stats/timeseries?from=2026-10-20&to=2026-10-10")
    assert res_inv.status_code == 422

    # > 366 days
    res_long = client.get("/api/stats/timeseries?from=2025-01-01&to=2026-02-15")
    assert res_long.status_code == 422
