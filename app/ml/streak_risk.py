"""Streak-risk prediction: estimates the probability of studying tomorrow."""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

FEATURE_COLS = [
    "is_weekend",
    "dow_sin",
    "dow_cos",
    "minutes_today",
    "minutes_yesterday",
    "rolling_7d_mean_minutes",
    "rolling_7d_study_count",
    "current_streak",
    "days_since_last_study",
    "freeze_available",
]

FEATURE_LABELS = {
    "is_weekend": "Weekend timing",
    "dow_sin": "Weekly rhythm cycle",
    "dow_cos": "Weekly rhythm cycle",
    "minutes_today": "Today's study volume",
    "minutes_yesterday": "Yesterday's study volume",
    "rolling_7d_mean_minutes": "7-day average study volume",
    "rolling_7d_study_count": "7-day study frequency",
    "current_streak": "Active streak momentum",
    "days_since_last_study": "Recency of last study day",
    "freeze_available": "Streak freeze cushion",
}


@dataclass
class RiskEvaluation:
    """Evaluation metrics comparing logistic regression against naive baselines."""

    accuracy: float
    f1: float
    brier_score: float
    baseline_majority_acc: float
    baseline_persistence_acc: float


def evaluate_classifier_chronological(X: "pd.DataFrame", y: "pd.Series") -> RiskEvaluation:
    """Perform leak-free chronological backtesting with TimeSeriesSplit."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, brier_score_loss, f1_score
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    n_splits = min(3, max(2, len(X) // 25))
    tscv = TimeSeriesSplit(n_splits=n_splits)

    accs, f1s, briers = [], [], []
    maj_accs, pers_accs = [], []

    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        if len(y_train.unique()) < 2 or len(y_test.unique()) < 1:
            continue

        clf = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(max_iter=200, random_state=42)),
            ]
        )
        clf.fit(X_train, y_train)

        preds = clf.predict(X_test)
        probs = clf.predict_proba(X_test)[:, 1]

        accs.append(accuracy_score(y_test, preds))
        f1s.append(f1_score(y_test, preds, zero_division=0))
        briers.append(brier_score_loss(y_test, probs))

        # Baseline A: Majority class in train set
        maj_class = y_train.mode()[0]
        maj_preds = np.full_like(y_test, maj_class)
        maj_accs.append(accuracy_score(y_test, maj_preds))

        # Baseline B: Persistence (tomorrow = today)
        pers_preds = (X_test["minutes_today"] > 0).astype(int)
        pers_accs.append(accuracy_score(y_test, pers_preds))

    if not accs:
        return RiskEvaluation(0.0, 0.0, 0.0, 0.0, 0.0)

    return RiskEvaluation(
        accuracy=round(float(np.mean(accs)), 3),
        f1=round(float(np.mean(f1s)), 3),
        brier_score=round(float(np.mean(briers)), 3),
        baseline_majority_acc=round(float(np.mean(maj_accs)), 3),
        baseline_persistence_acc=round(float(np.mean(pers_accs)), 3),
    )


def explain_top_factors(
    weights: "np.ndarray", feature_names: list[str], latest_row: "pd.Series"
) -> list[str]:
    """Translate top 3 standardized logistic regression coefficients into plain English."""
    import numpy as np

    order = np.argsort(np.abs(weights))[::-1]
    explanations = []

    for idx in order[:3]:
        feat = feature_names[idx]
        weight = weights[idx]
        val = latest_row.get(feat, 0)
        direction = "(+)" if weight > 0 else "(-)"

        if feat == "rolling_7d_study_count":
            explanations.append(f"Studied {int(val)} of last 7 days {direction}")
        elif feat == "current_streak":
            explanations.append(f"Streak momentum: {int(val)} days {direction}")
        elif feat == "days_since_last_study":
            explanations.append(f"Days since last study: {int(val)} {direction}")
        elif feat == "is_weekend":
            is_wknd = "Weekend" if val == 1 else "Weekday"
            explanations.append(f"{is_wknd} schedule pattern {direction}")
        elif feat == "rolling_7d_mean_minutes":
            explanations.append(f"7-day average: {int(val)} min/day {direction}")
        else:
            label = FEATURE_LABELS.get(feat, feat)
            explanations.append(f"{label} {direction}")

    return explanations


def compute_fallback_probability(features_df: "pd.DataFrame", tomorrow_weekday: int) -> float:
    """Bayesian smoothed day-of-week empirical study frequency."""
    import numpy as np

    if features_df.empty:
        return 0.50

    overall_rate = float(features_df["studied"].mean())
    a = max(0.2, overall_rate * 2.0)
    b = max(0.2, (1.0 - overall_rate) * 2.0)

    # Filter to identical weekday in history
    dow_records = features_df[features_df["day_of_week"] == tomorrow_weekday]
    if dow_records.empty:
        return round(float(overall_rate), 2)

    studied_dow_count = int(dow_records["studied"].sum())
    total_dow_count = len(dow_records)

    prob = (studied_dow_count + a) / (total_dow_count + a + b)
    return round(float(np.clip(prob, 0.05, 0.95)), 2)


def predict_streak_risk(features_df: "pd.DataFrame", today: date) -> dict:
    """Predict the probability that the user studies tomorrow."""
    import numpy as np
    import pandas as pd
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    data_days = len(features_df)
    tomorrow_weekday = (today.weekday() + 1) % 7

    confidence = "low"
    if data_days >= 60:
        confidence = "high"
    elif data_days >= 21:
        confidence = "medium"

    # Require at least 21 days of history and both classes present to fit ML model
    train_data = features_df.dropna(subset=["studied_next_day"])
    can_fit_ml = (
        data_days >= 21
        and len(train_data) >= 20
        and len(train_data["studied_next_day"].unique()) >= 2
    )

    if not can_fit_ml:
        prob = compute_fallback_probability(features_df, tomorrow_weekday)
        risk_level = "low" if prob >= 0.70 else ("medium" if prob >= 0.40 else "high")
        return {
            "probability_study_tomorrow": prob,
            "risk_level": risk_level,
            "top_factors": [
                f"Smoothed historical day-of-week rate ({int(prob * 100)}%)",
                f"Based on {data_days} days of logged activity",
                "Heuristic prior applied for cold-start",
            ],
            "model_used": "Empirical Bayesian Smoothed Frequency (Cold-Start Fallback)",
            "data_days": data_days,
            "confidence": confidence,
            "metrics": None,
        }

    # Prepare features and target
    X = train_data[FEATURE_COLS]
    y = train_data["studied_next_day"].astype(int)

    metrics = evaluate_classifier_chronological(X, y)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = LogisticRegression(class_weight="balanced", max_iter=200, random_state=42)
    clf.fit(X_scaled, y)

    # Predict for tomorrow using latest available row (today)
    latest_row = features_df.iloc[-1]
    X_latest = pd.DataFrame([latest_row[FEATURE_COLS]])
    X_latest_scaled = scaler.transform(X_latest)
    prob = float(clf.predict_proba(X_latest_scaled)[0, 1])
    prob = round(float(np.clip(prob, 0.02, 0.98)), 2)

    risk_level = "low" if prob >= 0.70 else ("medium" if prob >= 0.40 else "high")
    factors = explain_top_factors(clf.coef_[0], FEATURE_COLS, latest_row)

    return {
        "probability_study_tomorrow": prob,
        "risk_level": risk_level,
        "top_factors": factors,
        "model_used": "Standardized Logistic Regression (Balanced)",
        "data_days": data_days,
        "confidence": confidence,
        "metrics": {
            "accuracy": metrics.accuracy,
            "f1": metrics.f1,
            "brier_score": metrics.brier_score,
            "baseline_majority_accuracy": metrics.baseline_majority_acc,
            "baseline_persistence_accuracy": metrics.baseline_persistence_acc,
        },
    }
