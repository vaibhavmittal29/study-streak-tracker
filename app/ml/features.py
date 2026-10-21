"""Leakage-safe feature engineering pipeline for time-series study patterns."""

from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.services.streak_engine import compute_streaks

if TYPE_CHECKING:
    import pandas as pd


def build_daily_frame(
    sessions: list,
    start_date: date,
    end_date: date,
) -> "pd.DataFrame":
    """Build a zero-filled, chronologically ordered daily DataFrame.

    Each row corresponds to one calendar day with aggregated study minutes,
    session count, and a binary indicator whether study occurred.
    """
    import pandas as pd
    if start_date > end_date:
        raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

    # Map session objects or dicts
    day_minutes: dict[date, int] = {}
    day_counts: dict[date, int] = {}

    for s in sessions:
        s_date = s["date"] if isinstance(s, dict) else s.date
        s_mins = s["duration_minutes"] if isinstance(s, dict) else s.duration_minutes

        if start_date <= s_date <= end_date:
            day_minutes[s_date] = day_minutes.get(s_date, 0) + s_mins
            day_counts[s_date] = day_counts.get(s_date, 0) + 1

    records = []
    curr = start_date
    while curr <= end_date:
        mins = day_minutes.get(curr, 0)
        cnt = day_counts.get(curr, 0)
        records.append(
            {
                "date": curr,
                "minutes": mins,
                "n_sessions": cnt,
                "studied": 1 if mins >= 1 else 0,
            }
        )
        curr += timedelta(days=1)

    df = pd.DataFrame(records)
    return df


def make_features(
    df: "pd.DataFrame",
    freeze_enabled: bool = True,
) -> "pd.DataFrame":
    """Extract causal features using strictly past and current information (no leakage).

    Features generated for day t only depend on information available on or before day t.
    """
    import numpy as np

    if df.empty:
        return df

    out = df.copy()

    # Temporal features
    dow = out["date"].apply(lambda d: d.weekday())
    out["day_of_week"] = dow
    out["is_weekend"] = (dow >= 5).astype(int)

    # Cyclical day of week encoding
    out["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
    out["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)

    # Lags & Rolling statistics
    out["minutes_today"] = out["minutes"]
    out["minutes_yesterday"] = out["minutes"].shift(1).fillna(0)
    out["studied_yesterday"] = out["studied"].shift(1).fillna(0).astype(int)

    out["rolling_7d_mean_minutes"] = out["minutes"].rolling(window=7, min_periods=1).mean()
    out["rolling_7d_study_count"] = out["studied"].rolling(window=7, min_periods=1).sum()
    out["rolling_14d_study_rate"] = out["studied"].rolling(window=14, min_periods=1).mean()

    # Causal streak computation & days since last study
    study_dates_set: set[date] = set()
    streaks = []
    days_since_list = []
    freeze_avail_list = []

    last_studied_date: date | None = None

    for _, row in out.iterrows():
        d: date = row["date"]
        if row["studied"] == 1:
            study_dates_set.add(d)
            last_studied_date = d

        # Compute streak up to date d using pure engine
        res = compute_streaks(study_dates_set, d, freeze_enabled=freeze_enabled)
        streaks.append(res.current)
        freeze_avail_list.append(1 if res.freeze_available_this_week else 0)

        if last_studied_date is None:
            days_since_list.append(999)  # Large sentinel for cold start
        else:
            days_since_list.append((d - last_studied_date).days)

    out["current_streak"] = streaks
    out["days_since_last_study"] = days_since_list
    out["freeze_available"] = freeze_avail_list

    # Target for risk model: whether user studies tomorrow (shifted by -1)
    out["studied_next_day"] = out["studied"].shift(-1)

    return out
