"""Tests for synthetic data generation, global exception handling, and 5-year streak benchmark."""

import time
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.ml.synthetic import generate_synthetic_history
from app.models import StudySession


def test_synthetic_history_generation_deterministic() -> None:
    """Verify synthetic history generates deterministic results with identical seeds."""
    start = date(2026, 1, 1)
    end = date(2026, 3, 1)

    s1 = generate_synthetic_history(start, end, seed=123)
    s2 = generate_synthetic_history(start, end, seed=123)

    assert len(s1) > 0
    assert len(s1) == len(s2)
    assert s1[0]["subject"] == s2[0]["subject"]
    assert s1[0]["duration_minutes"] == s2[0]["duration_minutes"]


def test_global_exception_handler_masking() -> None:
    """Verify uncaught exceptions return sanitized 500 without leaking stack traces."""

    # Temporarily install a test route that raises an unhandled error
    @app.get("/api/test-error-endpoint")
    def trigger_error():
        raise RuntimeError("Secret internal database password leaked!")

    custom_client = TestClient(app, raise_server_exceptions=False)
    res = custom_client.get("/api/test-error-endpoint")
    assert res.status_code == 500
    assert res.json() == {"detail": "An internal server error occurred"}
    assert "Secret internal database password leaked!" not in res.text


def test_5_year_streak_api_performance_benchmark(
    client: TestClient, db_session, override_clock
) -> None:
    """Verify GET /api/streak executes in well under 100 ms with 5 years of data."""
    today = date(2026, 10, 20)
    override_clock(today)
    start_date = today - timedelta(days=1826)

    raw = generate_synthetic_history(start_date, today, seed=999)
    # Bulk insert
    db_session.bulk_save_objects(
        [
            StudySession(
                subject=r["subject"],
                subject_key=r["subject"].lower(),
                duration_minutes=r["duration_minutes"],
                date=r["date"],
                notes=r["notes"],
            )
            for r in raw
        ]
    )
    db_session.commit()

    # Benchmark API call
    t0 = time.perf_counter()
    res = client.get("/api/streak")
    duration_ms = (time.perf_counter() - t0) * 1000

    assert res.status_code == 200
    assert res.json()["current_streak"] >= 0
    assert duration_ms < 100.0, f"API took {duration_ms:.2f} ms (> 100 ms limit)"
