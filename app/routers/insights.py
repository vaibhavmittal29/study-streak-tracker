"""AI/ML insights endpoints: consistency forecast, streak risk, and recommendations."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.clock import get_clock, get_or_create_settings
from app.database import get_db
from app.ml.features import build_daily_frame, make_features
from app.ml.forecast import predict_forecast
from app.ml.recommendations import generate_recommendations
from app.ml.streak_risk import predict_streak_risk
from app.models import StudySession
from app.schemas import ForecastOut, RecommendationsListOut, StreakRiskOut

router = APIRouter(prefix="/api/insights", tags=["insights"])

# In-memory prediction and feature caches
_FEATURE_CACHE: dict[tuple, object] = {}
_RISK_CACHE: dict[tuple, dict] = {}
_FORECAST_CACHE: dict[tuple, dict] = {}
_RECS_CACHE: dict[tuple, list] = {}


def get_cache_key(db: Session, today: date) -> tuple:
    settings = get_or_create_settings(db)
    count, max_up = db.query(func.count(StudySession.id), func.max(StudySession.updated_at)).first()
    return (count, str(max_up), today.isoformat(), settings.freeze_enabled)


def get_cached_features(db: Session, today: date, cache_key: tuple | None = None):
    """Retrieve or build causal feature dataframe from database session records."""
    if cache_key is None:
        cache_key = get_cache_key(db, today)
    if cache_key in _FEATURE_CACHE:
        return _FEATURE_CACHE[cache_key]

    settings = get_or_create_settings(db)
    all_sessions = db.query(StudySession).all()
    if not all_sessions:
        start_date = today - timedelta(days=14)
    else:
        earliest_date = min(s.date for s in all_sessions)
        start_date = min(earliest_date, today - timedelta(days=21))

    daily_df = build_daily_frame(all_sessions, start_date, today)
    features_df = make_features(daily_df, freeze_enabled=settings.freeze_enabled)

    _FEATURE_CACHE[cache_key] = features_df
    return features_df


@router.get("/forecast", response_model=ForecastOut)
def get_study_forecast(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> dict:
    """Generate 7-day study minutes forecast using backtested time-series models."""
    key = get_cache_key(db, today)
    if key in _FORECAST_CACHE:
        return _FORECAST_CACHE[key]
    features_df = get_cached_features(db, today, key)
    result = predict_forecast(features_df, today)
    _FORECAST_CACHE[key] = result
    return result


@router.get("/streak-risk", response_model=StreakRiskOut)
def get_streak_risk(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> dict:
    """Predict tomorrow's study probability using standardized Logistic Regression."""
    key = get_cache_key(db, today)
    if key in _RISK_CACHE:
        return _RISK_CACHE[key]
    features_df = get_cached_features(db, today, key)
    result = predict_streak_risk(features_df, today)
    _RISK_CACHE[key] = result
    return result


@router.get("/recommendations", response_model=RecommendationsListOut)
def get_recommendations(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> dict:
    """Provide rule-based, explainable study recommendations backed by quantitative evidence."""
    key = get_cache_key(db, today)
    if key in _RECS_CACHE:
        return {"recommendations": _RECS_CACHE[key]}
    features_df = get_cached_features(db, today, key)
    recs = generate_recommendations(db, today, features_df)
    _RECS_CACHE[key] = recs
    return {"recommendations": recs}
