"""Tests for machine learning pipelines: feature engineering, leak-free evaluation,
streak-risk classification, forecasting, and recommendations.
"""

from datetime import date, timedelta

import numpy as np
from fastapi.testclient import TestClient

from app.clock import get_or_create_settings
from app.ml.features import build_daily_frame, make_features
from app.ml.forecast import predict_forecast
from app.ml.recommendations import generate_recommendations
from app.ml.streak_risk import predict_streak_risk
from app.ml.synthetic import generate_synthetic_history
from app.models import StudySession


def test_build_daily_frame_ordering_and_zerofill() -> None:
    """Verify daily frame is strictly zero-filled and ordered chronologically."""
    start = date(2026, 10, 15)
    end = date(2026, 10, 20)
    sessions = [
        {"subject": "DSA", "duration_minutes": 60, "date": date(2026, 10, 17)},
        {"subject": "Math", "duration_minutes": 45, "date": date(2026, 10, 20)},
    ]

    df = build_daily_frame(sessions, start, end)
    assert len(df) == 6
    assert list(df["date"]) == [start + timedelta(days=i) for i in range(6)]

    # Check zero-fills
    p0 = df[df["date"] == date(2026, 10, 15)].iloc[0]
    assert p0["minutes"] == 0 and p0["studied"] == 0

    p_studied = df[df["date"] == date(2026, 10, 17)].iloc[0]
    assert p_studied["minutes"] == 60 and p_studied["studied"] == 1


def test_no_data_leakage_in_features() -> None:
    """CRITICAL TEST: Modifying future data must not alter features of earlier days."""
    start = date(2026, 9, 1)
    end = date(2026, 10, 20)
    history_base = generate_synthetic_history(start, end, seed=42)

    df_base = build_daily_frame(history_base, start, end)
    feat_base = make_features(df_base)

    # Clone history and heavily alter days after October 10
    altered_history = [s for s in history_base if s["date"] <= date(2026, 10, 10)]
    # Add huge study sessions on Oct 15-20
    for d in range(15, 21):
        altered_history.append(
            {"subject": "AI", "duration_minutes": 300, "date": date(2026, 10, d)}
        )

    df_altered = build_daily_frame(altered_history, start, end)
    feat_altered = make_features(df_altered)

    # Compare features on October 10 and prior
    cutoff_idx = feat_base[feat_base["date"] == date(2026, 10, 10)].index[0]
    cols_to_check = [
        "rolling_7d_mean_minutes",
        "rolling_7d_study_count",
        "current_streak",
        "days_since_last_study",
        "freeze_available",
    ]

    for col in cols_to_check:
        np.testing.assert_array_equal(
            feat_base.loc[:cutoff_idx, col].values,
            feat_altered.loc[:cutoff_idx, col].values,
            err_msg=f"Data leakage detected in feature '{col}' prior to future modification!",
        )


def test_cold_start_fallback_when_history_short() -> None:
    """Verify models fall back gracefully when data is under 21 days."""
    today = date(2026, 10, 20)
    start = today - timedelta(days=10)
    history = generate_synthetic_history(start, today, seed=7)
    df = make_features(build_daily_frame(history, start, today))

    # Streak-risk should fall back
    risk = predict_streak_risk(df, today)
    assert risk["confidence"] == "low"
    assert "Fallback" in risk["model_used"] or "Smoothed" in risk["model_used"]
    assert 0.0 <= risk["probability_study_tomorrow"] <= 1.0

    # Forecast should fall back to weekday mean
    forecast = predict_forecast(df, today)
    assert forecast["confidence"] == "low"
    assert "Fallback" in forecast["model_used"]
    assert len(forecast["days"]) == 7


def test_models_with_sufficient_history() -> None:
    """Verify ML models train and output valid predictions with >= 60 days of data."""
    today = date(2026, 10, 20)
    start = today - timedelta(days=80)
    history = generate_synthetic_history(start, today, seed=42)
    df = make_features(build_daily_frame(history, start, today))

    # Risk model
    risk = predict_streak_risk(df, today)
    assert risk["confidence"] == "high"
    assert 0.0 <= risk["probability_study_tomorrow"] <= 1.0
    assert risk["risk_level"] in {"low", "medium", "high"}
    assert len(risk["top_factors"]) == 3
    assert risk["metrics"] is not None
    assert risk["metrics"]["accuracy"] >= 0.0

    # Forecast model
    fc = predict_forecast(df, today)
    assert fc["confidence"] == "high"
    assert len(fc["days"]) == 7
    assert all(d["predicted_minutes"] >= 0 for d in fc["days"])
    assert fc["weekly_total"] >= 0


def test_recommendation_rules(db_session) -> None:
    """Verify explainable recommendation rules trigger and provide quantitative evidence."""
    today = date(2026, 10, 20)

    # 1. Neglected subject rule (studied 7 days ago)
    db_session.add(
        StudySession(
            subject="Compiler Design",
            subject_key="compiler design",
            duration_minutes=60,
            date=date(2026, 10, 13),
        )
    )
    # Configure weekly goal of 300 minutes
    settings = get_or_create_settings(db_session)
    settings.weekly_goal_minutes = 300
    db_session.commit()

    recs = generate_recommendations(db_session, today, features_df=None)
    types = [r["type"] for r in recs]

    assert "neglected_subject" in types
    neglected_rec = next(r for r in recs if r["type"] == "neglected_subject")
    assert neglected_rec["evidence"]["subject"] == "Compiler Design"
    assert neglected_rec["evidence"]["days_ago"] == 7

    assert "goal_pace" in types
    goal_rec = next(r for r in recs if r["type"] == "goal_pace")
    assert goal_rec["evidence"]["weekly_goal"] == 300


def test_insights_api_endpoints(client: TestClient, override_clock) -> None:
    """Verify /api/insights endpoints respond with correct schemas."""
    today = date(2026, 10, 20)
    override_clock(today)

    # 1. Log a few sessions
    client.post(
        "/api/sessions",
        json={"subject": "DSA", "duration_minutes": 60, "date": "2026-10-18"},
    )
    client.post(
        "/api/sessions",
        json={"subject": "Math", "duration_minutes": 45, "date": "2026-10-20"},
    )

    # Forecast endpoint
    fc_res = client.get("/api/insights/forecast")
    assert fc_res.status_code == 200
    fc_data = fc_res.json()
    assert len(fc_data["days"]) == 7
    assert fc_data["weekly_total"] >= 0

    # Streak-risk endpoint
    risk_res = client.get("/api/insights/streak-risk")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert "probability_study_tomorrow" in risk_data
    assert "risk_level" in risk_data

    # Recommendations endpoint
    recs_res = client.get("/api/insights/recommendations")
    assert recs_res.status_code == 200
    recs_data = recs_res.json()
    assert "recommendations" in recs_data
    assert isinstance(recs_data["recommendations"], list)
