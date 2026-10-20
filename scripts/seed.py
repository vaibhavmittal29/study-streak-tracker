"""Script to seed realistic demonstration study sessions into SQLite database."""

import argparse
import sys
from datetime import timedelta
from pathlib import Path

# Add project root to sys.path so imports work when executed directly
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.clock import get_or_create_settings, get_today  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.ml.synthetic import generate_synthetic_history  # noqa: E402
from app.models import Settings, StudySession  # noqa: E402


def seed_database(days: int = 120, reset: bool = False) -> None:
    """Populate database with synthetic study records."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        if reset:
            print("[INFO] Resetting existing study sessions and settings...")
            db.query(StudySession).delete()
            db.query(Settings).delete()
            db.commit()

        user_settings = get_or_create_settings(db)
        user_settings.daily_goal_minutes = 90
        user_settings.weekly_goal_minutes = 600
        user_settings.freeze_enabled = True
        db.commit()

        today = get_today(user_settings.timezone)
        start_date = today - timedelta(days=days)

        print(f"[INFO] Generating ~{days} days of realistic synthetic data...")
        raw_sessions = generate_synthetic_history(start_date, today, seed=42)

        for s in raw_sessions:
            session_obj = StudySession(
                subject=s["subject"],
                subject_key=s["subject"].lower(),
                duration_minutes=s["duration_minutes"],
                date=s["date"],
                notes=s["notes"],
            )
            db.add(session_obj)

        db.commit()
        total_count = db.query(StudySession).count()

        print("\n" + "=" * 60)
        print("          DEMO DATA GENERATION COMPLETED")
        print("=" * 60)
        print(f"Total Sessions in DB : {total_count}")
        print(f"Date Range Covered   : {start_date} to {today}")
        print(f"Timezone Configured  : {user_settings.timezone}")
        print(
            f"Daily / Weekly Goals : {user_settings.daily_goal_minutes}m / "
            f"{user_settings.weekly_goal_minutes}m"
        )
        print("=" * 60 + "\n")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed database with realistic demo study history."
    )
    parser.add_argument(
        "--days", type=int, default=120, help="Number of past days to generate (default: 120)"
    )
    parser.add_argument(
        "--reset", action="store_true", help="Wipe existing records before seeding"
    )
    args = parser.parse_args()

    seed_database(days=args.days, reset=args.reset)
