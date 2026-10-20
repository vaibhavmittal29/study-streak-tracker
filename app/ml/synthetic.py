"""Synthetic study history generator for realistic demonstration data and tests."""

import random
from datetime import date, timedelta

SUBJECTS = [
    "DSA",
    "Operating Systems",
    "Computer Networks",
    "Database Systems",
    "Linear Algebra",
    "Machine Learning",
]

NOTES_SAMPLES = [
    "Reviewed lecture notes and solved practice questions",
    "Completed lab assignment exercises",
    "Implemented algorithm from scratch and tested edge cases",
    "Read textbook chapter and summarized key theorems",
    "Solved LeetCode daily problem and optimized complexity",
]


def generate_synthetic_history(
    start_date: date,
    end_date: date,
    seed: int = 42,
) -> list[dict]:
    """Generate realistic study sessions over a date range using a fixed seed.

    Mimics student habits: higher study probability on weekdays, occasional multi-session
    days, subject rotation, and occasional natural lapses.
    """
    rng = random.Random(seed)
    sessions: list[dict] = []

    curr = start_date
    lapse_days_left = 0

    while curr <= end_date:
        # Check if in an intentional lapse
        if lapse_days_left > 0:
            lapse_days_left -= 1
            curr += timedelta(days=1)
            continue

        # 5% chance of starting a 2-day lapse
        if rng.random() < 0.05:
            lapse_days_left = 1
            curr += timedelta(days=1)
            continue

        is_weekend = curr.weekday() >= 5
        study_prob = 0.55 if is_weekend else 0.78

        if rng.random() < study_prob:
            # 20% chance of 2 sessions on this day
            n_sessions = 2 if rng.random() < 0.20 else 1
            remaining_day_budget = 360  # max 6 hours across sessions

            for _ in range(n_sessions):
                subject = rng.choice(SUBJECTS)
                mean_dur = 60 if is_weekend else 90
                dur = int(rng.gauss(mean_dur, 25))
                dur = max(20, min(dur, remaining_day_budget))

                notes = rng.choice(NOTES_SAMPLES) if rng.random() < 0.6 else None
                sessions.append(
                    {
                        "subject": subject,
                        "duration_minutes": dur,
                        "date": curr,
                        "notes": notes,
                    }
                )
                remaining_day_budget -= dur
                if remaining_day_budget < 20:
                    break

        curr += timedelta(days=1)

    return sessions
