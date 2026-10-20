"""Endpoints for study statistics and chart time series."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.clock import get_clock
from app.database import get_db
from app.schemas import TimeSeriesOut, WeeklyStatsOut
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/weekly", response_model=WeeklyStatsOut)
def get_weekly_statistics(
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> WeeklyStatsOut:
    """Return subject breakdown and total minutes for the active ISO week."""
    return stats_service.weekly_totals(db, today)


@router.get("/timeseries", response_model=TimeSeriesOut)
def get_timeseries_statistics(
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    granularity: Annotated[str, Query(pattern="^(day|week)$")] = "day",
    db: Session = Depends(get_db),
    today: date = Depends(get_clock),
) -> TimeSeriesOut:
    """Return zero-filled time series data points for charts.

    Defaults to the past 30 days ending today.
    """
    effective_to = to_date or today
    effective_from = from_date or (effective_to - timedelta(days=29))
    return stats_service.timeseries(db, effective_from, effective_to, granularity)
