"""Rule-based, explainable study habit recommendations."""

from datetime import date

from sqlalchemy.orm import Session

from app.clock import get_or_create_settings
from app.models import StudySession
from app.services.streak_engine import compute_streaks

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def generate_recommendations(
    db: Session,
    today: date,
    features_df,
) -> list[dict]:
    """Produce actionable, explainable suggestions backed by quantitative evidence."""
    recommendations: list[dict] = []
    settings = get_or_create_settings(db)

    # 1. Neglected Subject Check: studied previously, but not in the last 5+ days
    all_sessions = db.query(StudySession).order_by(StudySession.date.desc()).all()
    if all_sessions:
        subject_last_seen: dict[str, tuple[str, date]] = {}
        for s in all_sessions:
            if s.subject_key not in subject_last_seen:
                subject_last_seen[s.subject_key] = (s.subject, s.date)

        for _, (display_name, last_d) in subject_last_seen.items():
            days_ago = (today - last_d).days
            if days_ago >= 5:
                recommendations.append(
                    {
                        "type": "neglected_subject",
                        "message": (
                            f"You haven't studied '{display_name}' in {days_ago} days. "
                            "Consider scheduling a brief review session today."
                        ),
                        "evidence": {
                            "subject": display_name,
                            "last_studied": last_d.isoformat(),
                            "days_ago": days_ago,
                        },
                    }
                )
                break  # Show the most overdue subject

    # 2. Weekly Goal Pacing Check
    if settings.weekly_goal_minutes is not None:
        from app.services.goals_service import compute_goal_progress

        progress = compute_goal_progress(db, today)
        weekly = progress.weekly
        if weekly and not weekly.met and weekly.remaining > 0:
            recommendations.append(
                {
                    "type": "goal_pace",
                    "message": (
                        f"You need ~{weekly.required_per_day} min/day for the rest of the week "
                        f"to hit your weekly target of {weekly.goal_minutes}m."
                    ),
                    "evidence": {
                        "weekly_goal": weekly.goal_minutes,
                        "done_minutes": weekly.done_minutes,
                        "remaining_minutes": weekly.remaining,
                        "days_left": weekly.days_left_including_today,
                        "required_per_day": weekly.required_per_day,
                    },
                }
            )

    # 3. Streak at Risk & Freeze Advisory Check
    distinct_dates = {row[0] for row in db.query(StudySession.date).distinct().all()}
    streak_res = compute_streaks(distinct_dates, today, freeze_enabled=settings.freeze_enabled)
    if streak_res.at_risk and streak_res.current >= 3:
        if streak_res.freeze_available_this_week:
            freeze_note = "Your weekly freeze is available as a safety net if needed."
        else:
            freeze_note = (
                "Your weekly freeze was already used, so missing today will reset your streak!"
            )

        recommendations.append(
            {
                "type": "streak_at_risk",
                "message": (
                    f"You have an active {streak_res.current}-day streak! "
                    f"Log at least 1 minute today to keep it going. {freeze_note}"
                ),
                "evidence": {
                    "current_streak": streak_res.current,
                    "studied_today": streak_res.studied_today,
                    "freeze_available": streak_res.freeze_available_this_week,
                },
            }
        )

    # 4. Best Weekday Insight (requires >= 28 days of history)
    if features_df is not None and len(features_df) >= 28:
        dow_avg = features_df.groupby("day_of_week")["minutes"].mean()
        best_dow = int(dow_avg.idxmax())
        best_dow_name = WEEKDAY_NAMES[best_dow]
        best_avg_min = int(round(dow_avg.max()))

        recommendations.append(
            {
                "type": "best_weekday",
                "message": (
                    f"{best_dow_name} is your most productive day, averaging {best_avg_min} "
                    "minutes. Leverage this day for deeper, complex topics."
                ),
                "evidence": {
                    "best_weekday": best_dow_name,
                    "average_minutes": best_avg_min,
                    "historical_weeks": len(features_df) // 7,
                },
            }
        )

    # 5. Consistency Metric over Last 14 Days
    if features_df is not None and len(features_df) >= 7:
        last_14 = features_df.tail(14)
        studied_days = int(last_14["studied"].sum())
        total_days = len(last_14)
        rate = round((studied_days / total_days) * 100, 1)

        recommendations.append(
            {
                "type": "consistency_rate",
                "message": (
                    f"You studied on {studied_days} of the past {total_days} days "
                    f"({rate}% consistency rate)."
                ),
                "evidence": {
                    "studied_days": studied_days,
                    "total_days": total_days,
                    "consistency_percentage": rate,
                },
            }
        )

    return recommendations
