"""7-day study time forecasting with rolling-origin candidate backtesting."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error


def seasonal_naive_forecast(series: pd.Series, horizon: int = 7) -> list[float]:
    """Seasonal naive: predict identical weekday from 7 days ago."""
    if len(series) < 7:
        avg = float(series.mean()) if not series.empty else 60.0
        return [max(0.0, avg)] * horizon
    return [float(max(0.0, series.iloc[-7 + (i % 7)])) for i in range(horizon)]


def weekday_mean_forecast(df: pd.DataFrame, horizon: int = 7) -> list[float]:
    """Weekday mean: average minutes on that specific day-of-week over recent history."""
    if df.empty:
        return [60.0] * horizon

    if "day_of_week" not in df.columns and "date" in df.columns:
        df = df.copy()
        df["day_of_week"] = df["date"].apply(lambda d: d.weekday())

    last_date = df["date"].iloc[-1]
    means = df.groupby("day_of_week")["minutes"].mean().to_dict()
    global_mean = float(df["minutes"].mean())

    preds = []
    for i in range(1, horizon + 1):
        target_date = last_date + timedelta(days=i)
        target_dow = target_date.weekday()
        val = means.get(target_dow, global_mean)
        preds.append(float(max(0.0, val)))
    return preds


def ewma_weekday_forecast(df: pd.DataFrame, horizon: int = 7) -> list[float]:
    """EWMA level adjusted by empirical weekday multiplicative factors."""
    if len(df) < 7:
        return weekday_mean_forecast(df, horizon)

    if "day_of_week" not in df.columns and "date" in df.columns:
        df = df.copy()
        df["day_of_week"] = df["date"].apply(lambda d: d.weekday())

    ewma_level = float(df["minutes"].ewm(span=14, min_periods=1).mean().iloc[-1])
    mean_val = max(1.0, float(df["minutes"].mean()))

    dow_ratios = (df.groupby("day_of_week")["minutes"].mean() / mean_val).to_dict()
    last_date = df["date"].iloc[-1]

    preds = []
    for i in range(1, horizon + 1):
        target_date = last_date + timedelta(days=i)
        ratio = dow_ratios.get(target_date.weekday(), 1.0)
        preds.append(float(max(0.0, ewma_level * ratio)))
    return preds


def ridge_lag_forecast(df: pd.DataFrame, horizon: int = 7) -> list[float]:
    """Autoregressive Ridge model on lag and rolling features."""
    if len(df) < 28:
        return weekday_mean_forecast(df, horizon)

    temp = df[["minutes"]].copy()
    temp["lag_1"] = temp["minutes"].shift(1)
    temp["lag_7"] = temp["minutes"].shift(7)
    temp["lag_14"] = temp["minutes"].shift(14)
    temp["roll_mean"] = temp["minutes"].shift(1).rolling(7).mean()

    valid = temp.dropna()
    if len(valid) < 14:
        return weekday_mean_forecast(df, horizon)

    X = valid[["lag_1", "lag_7", "lag_14", "roll_mean"]]
    y = valid["minutes"]

    model = Ridge(alpha=1.0)
    model.fit(X, y)

    # Multi-step iterative autoregressive rollout
    history = list(temp["minutes"].values)
    preds = []
    for _ in range(horizon):
        lag_1 = history[-1]
        lag_7 = history[-7] if len(history) >= 7 else lag_1
        lag_14 = history[-14] if len(history) >= 14 else lag_7
        roll = float(np.mean(history[-7:]))
        step_feat = pd.DataFrame([[lag_1, lag_7, lag_14, roll]], columns=X.columns)
        pred_val = float(max(0.0, model.predict(step_feat)[0]))
        preds.append(pred_val)
        history.append(pred_val)

    return preds


def backtest_candidates(df: pd.DataFrame) -> tuple[str, float, float]:
    """Run rolling-origin backtest on the last ~28 days to pick best model by MAE.

    Returns: (best_candidate_name, best_mae, baseline_naive_mae)
    """
    if "day_of_week" not in df.columns and "date" in df.columns:
        df = df.copy()
        df["day_of_week"] = df["date"].apply(lambda d: d.weekday())

    if len(df) < 35:
        # History too short for meaningful backtest
        return ("Weekday Mean (Empirical)", 0.0, 0.0)

    naive_errors = []
    wkday_errors = []
    ewma_errors = []
    ridge_errors = []

    for cutoff in [len(df) - 21, len(df) - 14, len(df) - 7]:
        train_df = df.iloc[:cutoff]
        actual = df.iloc[cutoff : cutoff + 7]["minutes"].values

        p_naive = seasonal_naive_forecast(train_df["minutes"], horizon=7)
        p_wkday = weekday_mean_forecast(train_df, horizon=7)
        p_ewma = ewma_weekday_forecast(train_df, horizon=7)
        p_ridge = ridge_lag_forecast(train_df, horizon=7)

        naive_errors.append(mean_absolute_error(actual, p_naive))
        wkday_errors.append(mean_absolute_error(actual, p_wkday))
        ewma_errors.append(mean_absolute_error(actual, p_ewma))
        ridge_errors.append(mean_absolute_error(actual, p_ridge))

    mae_naive = float(np.mean(naive_errors))
    mae_wkday = float(np.mean(wkday_errors))
    mae_ewma = float(np.mean(ewma_errors))
    mae_ridge = float(np.mean(ridge_errors))

    candidates = [
        ("Seasonal Naive (t-7)", mae_naive),
        ("Weekday Mean (Empirical)", mae_wkday),
        ("EWMA Level x Weekday Factor", mae_ewma),
        ("Autoregressive Ridge", mae_ridge),
    ]

    candidates.sort(key=lambda x: x[1])
    best_name, best_mae = candidates[0]
    return (best_name, round(best_mae, 1), round(mae_naive, 1))


def predict_forecast(df: pd.DataFrame, today: date) -> dict:
    """Generate 7-day study minutes forecast using the backtest-winning model."""
    data_days = len(df)

    confidence = "low"
    if data_days >= 60:
        confidence = "high"
    elif data_days >= 21:
        confidence = "medium"

    if data_days < 14:
        preds = weekday_mean_forecast(df, horizon=7)
        best_model = "Weekday Mean (Cold-Start Fallback)"
        best_mae = 0.0
        baseline_mae = 0.0
    else:
        best_model, best_mae, baseline_mae = backtest_candidates(df)
        if "Ridge" in best_model:
            preds = ridge_lag_forecast(df, horizon=7)
        elif "EWMA" in best_model:
            preds = ewma_weekday_forecast(df, horizon=7)
        elif "Seasonal" in best_model:
            preds = seasonal_naive_forecast(df["minutes"], horizon=7)
        else:
            preds = weekday_mean_forecast(df, horizon=7)

    # Prepare daily output array
    days_out = []
    for i, p in enumerate(preds, start=1):
        target_date = today + timedelta(days=i)
        days_out.append(
            {
                "date": target_date.isoformat(),
                "predicted_minutes": int(round(p)),
            }
        )

    weekly_total = sum(d["predicted_minutes"] for d in days_out)

    return {
        "days": days_out,
        "weekly_total": weekly_total,
        "model_used": best_model,
        "backtest_mae": best_mae,
        "baseline_mae": baseline_mae,
        "data_days": data_days,
        "confidence": confidence,
    }
