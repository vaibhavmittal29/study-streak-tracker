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

# In-memory feature cache: {(count, max_updated_at, today): features_df}
_FEATURE_CACHE: dict[tuple, tuple] = {}


def get_cached_features(db: Session, today: date):
    """Retrieve or build causal feature dataframe from database session records."""
    settings = get_or_create_settings(db)
    count, max_up = db.query(func.count(StudySession.id), func.max(StudySession.updated_at)).first()

    cache_key = (count, str(max_up), today.isoformat(), settings.freeze_enabled)
    if cache_key in _FEATURE_CACHE:
        return _FEATURE_CACHE[cache_key]

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
    features_df = get_cached_features(db, today)
    return predict_forecast(features_df, today)


@router.get("/streak-risk", response_model=StreakRiskOut)
def get_streak_risk(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> dict:
    """Predict tomorrow's study probability using standardized Logistic Regression."""
    features_df = get_cached_features(db, today)
    return predict_streak_risk(features_df, today)


@router.get("/recommendations", response_model=RecommendationsListOut)
def get_recommendations(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> dict:
    """Provide rule-based, explainable study recommendations backed by quantitative evidence."""
    features_df = get_cached_features(db, today)
    recs = generate_recommendations(db, today, features_df)
    return {"recommendations": recs}
