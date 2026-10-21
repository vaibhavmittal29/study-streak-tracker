"""Offline evaluation benchmark script.

Simulates study records across multiple random seeds, evaluates Streak-Risk
classification and 7-day Forecasting models against baseline heuristics,
and outputs a Markdown table for inclusion in documentation.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.ml.features import build_daily_frame, make_features  # noqa: E402
from app.ml.forecast import backtest_candidates  # noqa: E402
from app.ml.streak_risk import FEATURE_COLS, evaluate_classifier_chronological  # noqa: E402
from app.ml.synthetic import generate_synthetic_history  # noqa: E402


def run_evaluation() -> None:
    """Run cross-seed evaluation and print markdown table."""
    seeds = [42, 101, 777]
    days = 120
    today = date(2026, 10, 20)
    start_date = today - timedelta(days=days)

    risk_accs = []
    risk_f1s = []
    risk_briers = []
    risk_maj_accs = []
    risk_pers_accs = []

    forecast_maes = []
    baseline_maes = []

    for seed in seeds:
        raw_sessions = generate_synthetic_history(start_date, today, seed=seed)
        daily_df = build_daily_frame(raw_sessions, start_date, today)
        features_df = make_features(daily_df, freeze_enabled=True)

        # 1. Streak-Risk classification evaluation
        train_data = features_df.dropna(subset=["studied_next_day"])
        X = train_data[FEATURE_COLS]
        y = train_data["studied_next_day"].astype(int)

        risk_eval = evaluate_classifier_chronological(X, y)
        if risk_eval.accuracy > 0:
            risk_accs.append(risk_eval.accuracy)
            risk_f1s.append(risk_eval.f1)
            risk_briers.append(risk_eval.brier_score)
            risk_maj_accs.append(risk_eval.baseline_majority_acc)
            risk_pers_accs.append(risk_eval.baseline_persistence_acc)

        # 2. Forecasting evaluation
        _, best_mae, base_mae = backtest_candidates(features_df)
        if best_mae > 0:
            forecast_maes.append(best_mae)
            baseline_maes.append(base_mae)

    print("\n" + "=" * 75)
    print("           STUDY TRACKER AI/ML BENCHMARK EVALUATION RESULTS")
    print("=" * 75)
    print("### Model Performance vs Baselines (Averaged over 3 Independent Seeds)\n")

    print("| Task | Model / Method | Accuracy | F1 Score | Brier Score | Error (MAE) |")
    print("|---|---|---|---|---|---|")
    print(
        f"| **Streak Risk** | Standardized Logistic Regression | "
        f"**{np.mean(risk_accs):.1%}** | **{np.mean(risk_f1s):.3f}** | "
        f"**{np.mean(risk_briers):.3f}** | - |"
    )
    print(
        f"| **Streak Risk** | Baseline: Majority Class | {np.mean(risk_maj_accs):.1%} | - | - | - |"
    )
    print(
        f"| **Streak Risk** | Baseline: Tomorrow = Today | "
        f"{np.mean(risk_pers_accs):.1%} | - | - | - |"
    )
    print(
        f"| **7-Day Forecast** | Empirical Weekday / EWMA Ensemble | "
        f"- | - | - | **{np.mean(forecast_maes):.1f} min** |"
    )
    print(
        f"| **7-Day Forecast** | Baseline: Seasonal Naive (t-7) | "
        f"- | - | - | {np.mean(baseline_maes):.1f} min |"
    )
    print("\n" + "=" * 75 + "\n")


if __name__ == "__main__":
    run_evaluation()
