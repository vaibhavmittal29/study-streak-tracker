"""Demo mode automated seeder: guarantees rich, deterministic demonstration data."""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.clock import get_or_create_settings
from app.ml.synthetic import generate_synthetic_history
from app.models import StudySession


def seed_demo_data(db: Session, today: date, reset: bool = False) -> int:
    """Seed ~120 days of realistic study sessions ending strictly YESTERDAY.

    Guarantees:
    - Active current streak of several days (e.g. 5 days) ending yesterday.
    - Today has 0 sessions, so today is alive but 'at risk' (studied_today=False).
    - Visible freeze used in recent weeks (frozen_dates populated).
    - Longest streak from earlier history is longer than current streak (e.g. 12 days).
    - Diverse subjects and occasional multi-session days.
    - Daily goal (90m) and weekly goal (600m) configured.
    """
    if reset:
        db.query(StudySession).delete()
        db.commit()

    existing_count = db.query(StudySession).count()
    if existing_count > 0 and not reset:
        return existing_count

    # 1. Ensure settings
    user_settings = get_or_create_settings(db)
    user_settings.daily_goal_minutes = 90
    user_settings.weekly_goal_minutes = 600
    user_settings.freeze_enabled = True
    db.commit()

    yesterday = today - timedelta(days=1)
    start_date = yesterday - timedelta(days=120)

    # 2. Generate base realistic history using fixed seed
    raw_sessions = generate_synthetic_history(start_date, yesterday, seed=42)

    # Filter out any session that accidentally fell on or after today
    valid_sessions = [s for s in raw_sessions if s["date"] <= yesterday]

    # Ensure past 5 days ending yesterday are consecutive study days for an active streak
    active_run_dates = {yesterday - timedelta(days=i) for i in range(5)}
    dates_with_sessions = {s["date"] for s in valid_sessions}

    for run_d in active_run_dates:
        if run_d not in dates_with_sessions:
            valid_sessions.append(
                {
                    "subject": "DSA",
                    "duration_minutes": 75,
                    "date": run_d,
                    "notes": "Problem solving session",
                }
            )

    # Ensure a 1-day miss happened 8 days ago to visibly consume a freeze
    freeze_miss_date = yesterday - timedelta(days=7)
    valid_sessions = [s for s in valid_sessions if s["date"] != freeze_miss_date]

    # Ensure a historical 12-day run ~60 days ago so longest > current
    long_run_start = start_date + timedelta(days=20)
    for i in range(12):
        d = long_run_start + timedelta(days=i)
        if d not in {s["date"] for s in valid_sessions}:
            valid_sessions.append(
                {
                    "subject": "Algorithms" if i % 2 == 0 else "Operating Systems",
                    "duration_minutes": 60,
                    "date": d,
                    "notes": "Intensive sprint session",
                }
            )

    # Sort and commit
    valid_sessions.sort(key=lambda s: s["date"])

    for s in valid_sessions:
        session_obj = StudySession(
            subject=s["subject"],
            subject_key=s["subject"].lower(),
            duration_minutes=s["duration_minutes"],
            date=s["date"],
            notes=s.get("notes"),
        )
        db.add(session_obj)

    db.commit()
    return db.query(StudySession).count()
