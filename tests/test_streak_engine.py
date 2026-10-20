"""Unit tests for the pure streak engine covering the edge-case matrix (E1-E22)."""

import random
import time
from datetime import date, timedelta

from app.services.streak_engine import StreakResult, compute_streaks, week_key


def test_e1_no_sessions() -> None:
    """E1: No sessions -> current 0, longest 0, at_risk False."""
    today = date(2026, 10, 20)
    res = compute_streaks(set(), today, freeze_enabled=True)
    assert res == StreakResult(
        current=0,
        longest=0,
        studied_today=False,
        at_risk=False,
        last_study_date=None,
        frozen_dates=(),
        freeze_available_this_week=True,
    )


def test_e2_only_today() -> None:
    """E2: Only today -> current 1, longest 1, studied_today True, at_risk False."""
    today = date(2026, 10, 20)
    res = compute_streaks({today}, today, freeze_enabled=True)
    assert res.current == 1
    assert res.longest == 1
    assert res.studied_today is True
    assert res.at_risk is False
    assert res.last_study_date == today
    assert res.frozen_dates == ()
    assert res.freeze_available_this_week is True


def test_e3_only_yesterday_none_today() -> None:
    """E3: Only yesterday, none today -> current 1 (alive), at_risk True."""
    today = date(2026, 10, 20)
    yesterday = date(2026, 10, 19)
    res = compute_streaks({yesterday}, today, freeze_enabled=True)
    assert res.current == 1
    assert res.longest == 1
    assert res.studied_today is False
    assert res.at_risk is True
    assert res.last_study_date == yesterday
    assert res.frozen_dates == ()


def test_e4_last_study_2_days_ago_freeze_on() -> None:
    """E4: Last study 2 days ago, freeze on -> day-1 frozen, current preserved."""
    today = date(2026, 10, 21)  # Wednesday
    day_minus_2 = date(2026, 10, 19)  # Monday
    day_minus_1 = date(2026, 10, 20)  # Tuesday (missed)

    res = compute_streaks({day_minus_2}, today, freeze_enabled=True)
    assert res.current == 1
    assert res.longest == 1
    assert res.studied_today is False
    assert res.at_risk is True
    assert res.frozen_dates == (day_minus_1,)
    assert res.freeze_available_this_week is False


def test_e5_last_study_2_days_ago_freeze_off() -> None:
    """E5: Last study 2 days ago, freeze off -> current 0."""
    today = date(2026, 10, 21)
    day_minus_2 = date(2026, 10, 19)

    res = compute_streaks({day_minus_2}, today, freeze_enabled=False)
    assert res.current == 0
    assert res.longest == 1
    assert res.studied_today is False
    assert res.at_risk is False
    assert res.frozen_dates == ()
    assert res.freeze_available_this_week is False


def test_e6_last_study_3_days_ago_freeze_on() -> None:
    """E6: Last study 3 days ago, freeze on -> second miss breaks streak -> current 0."""
    today = date(2026, 10, 22)  # Thursday
    day_minus_3 = date(2026, 10, 19)  # Monday

    res = compute_streaks({day_minus_3}, today, freeze_enabled=True)
    assert res.current == 0
    assert res.longest == 1
    assert res.studied_today is False
    assert res.at_risk is False


def test_e7_several_sessions_in_one_day() -> None:
    """E7: Multiple sessions on the same day count as one study day."""
    today = date(2026, 10, 20)
    # Set of dates naturally deduplicates multiple sessions on the same calendar date
    dates = {date(2026, 10, 19), date(2026, 10, 19), date(2026, 10, 20)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 2
    assert res.longest == 2


def test_e8_n_consecutive_days_ending_today() -> None:
    """E8: N consecutive days ending today -> current N, longest N."""
    today = date(2026, 10, 20)
    n = 10
    dates = {today - timedelta(days=i) for i in range(n)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == n
    assert res.longest == n
    assert res.studied_today is True
    assert res.at_risk is False


def test_e9_missed_day_mid_streak_freeze_off() -> None:
    """E9: Missed day mid-streak, freeze off -> resets, longest preserves earlier run."""
    today = date(2026, 10, 20)
    # Studied Oct 10..14 (5 days), missed Oct 15, studied Oct 16..20 (5 days)
    run1 = {date(2026, 10, d) for d in range(10, 15)}
    run2 = {date(2026, 10, d) for d in range(16, 21)}
    dates = run1 | run2

    res = compute_streaks(dates, today, freeze_enabled=False)
    assert res.current == 5
    assert res.longest == 5


def test_e10_missed_day_mid_streak_freeze_on() -> None:
    """E10: Missed day mid-streak, freeze on -> continues, length unchanged on frozen day."""
    # Week: Mon Oct 12 to Sun Oct 18
    today = date(2026, 10, 15)  # Thu
    # Mon 12 (studied), Tue 13 (studied), Wed 14 (missed, frozen), Thu 15 (studied)
    dates = {date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 15)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    # Mon(+1), Tue(+1), Wed(freeze, +0), Thu(+1) => current 3
    assert res.current == 3
    assert res.longest == 3
    assert res.frozen_dates == (date(2026, 10, 14),)
    assert res.freeze_available_this_week is False


def test_e11_two_misses_in_same_iso_week() -> None:
    """E11: Two misses in the same ISO week -> second miss breaks streak."""
    # Week: Mon Oct 12 to Sun Oct 18
    # Mon 12 (study), Tue 13 (miss 1 -> freeze), Wed 14 (miss 2 -> breaks), Thu 15 (study)
    today = date(2026, 10, 15)
    dates = {date(2026, 10, 12), date(2026, 10, 15)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 1
    assert res.longest == 1
    assert date(2026, 10, 13) in res.frozen_dates


def test_e12_miss_on_sunday_and_monday_across_iso_weeks() -> None:
    """E12: Miss on Sunday + Monday -> both frozen because they fall in different ISO weeks."""
    # Sat Oct 17 (study), Sun Oct 18 (miss, ISO week 42 freeze),
    # Mon Oct 19 (miss, ISO week 43 freeze), Tue Oct 20 (today, study)
    today = date(2026, 10, 20)
    dates = {date(2026, 10, 17), date(2026, 10, 20)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 2
    assert res.frozen_dates == (date(2026, 10, 18), date(2026, 10, 19))


def test_e13_freeze_not_consumed_when_current_is_zero() -> None:
    """E13: Freeze not consumed when current == 0 (gaps before first study are ignored)."""
    # First ever session is Oct 20
    today = date(2026, 10, 20)
    dates = {date(2026, 10, 20)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 1
    assert res.frozen_dates == ()
    assert res.freeze_available_this_week is True


def test_e14_iso_year_boundary() -> None:
    """E14: ISO year boundary (e.g. 28 Dec 2025 to 4 Jan 2026) handles week keys cleanly."""
    # 2025-12-28 is Sunday of ISO week (2025, 52)
    # 2025-12-29 is Monday of ISO week (2025, 1) or (2026, 1)
    d1 = date(2025, 12, 28)
    d2 = date(2025, 12, 29)
    assert week_key(d1) != week_key(d2)

    # Studied Dec 28, missed Dec 29 (week 1 freeze), studied Dec 30
    today = date(2025, 12, 30)
    dates = {date(2025, 12, 28), date(2025, 12, 30)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 2
    assert res.frozen_dates == (date(2025, 12, 29),)


def test_e19_future_dates_defensively_ignored() -> None:
    """E19: Future dates are ignored defensively by the engine."""
    today = date(2026, 10, 20)
    dates = {date(2026, 10, 20), date(2026, 10, 25), date(2026, 11, 1)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 1
    assert res.longest == 1
    assert res.last_study_date == today


def test_e20_leap_day_in_streak() -> None:
    """E20: Leap day (29 Feb 2028) counted accurately in run."""
    today = date(2028, 3, 1)
    dates = {date(2028, 2, 28), date(2028, 2, 29), date(2028, 3, 1)}
    res = compute_streaks(dates, today, freeze_enabled=True)
    assert res.current == 3
    assert res.longest == 3


def test_e21_performance_5_years_under_50ms() -> None:
    """E21: Computing streaks for 5 years (~1826 days) finishes well under 50 ms."""
    today = date(2026, 10, 20)
    start_date = today - timedelta(days=1826)
    # Realistic density: studied 70% of days
    rng = random.Random(42)
    study_dates = {
        start_date + timedelta(days=i)
        for i in range(1826)
        if rng.random() > 0.3
    }
    study_dates.add(today)

    t0 = time.perf_counter()
    res = compute_streaks(study_dates, today, freeze_enabled=True)
    duration_ms = (time.perf_counter() - t0) * 1000

    assert res.current > 0
    assert duration_ms < 50.0, f"Streak engine took {duration_ms:.2f} ms (> 50 ms)"


def test_e22_longest_streak_ended_in_past() -> None:
    """E22: When a longer streak ended in the past, longest > current."""
    today = date(2026, 10, 20)
    # Long streak in January (15 days)
    long_streak = {date(2026, 1, d) for d in range(1, 16)}
    # Small streak now (2 days)
    recent_streak = {date(2026, 10, 19), date(2026, 10, 20)}
    res = compute_streaks(long_streak | recent_streak, today, freeze_enabled=True)
    assert res.current == 2
    assert res.longest == 15
    assert res.longest > res.current


# --- Brute-force reference implementation and randomized property test ---

def naive_streak_simulator(
    study_dates: set[date], today: date, freeze_enabled: bool = True
) -> tuple[int, int]:
    """Deliberately simple, day-by-day reference simulator for property testing."""
    dates = {d for d in study_dates if d <= today}
    if not dates:
        return (0, 0)

    start = min(dates)
    curr = 0
    longest = 0
    used_weeks = set()

    d = start
    while d < today:
        if d in dates:
            curr += 1
        elif freeze_enabled and curr > 0 and week_key(d) not in used_weeks:
            used_weeks.add(week_key(d))
        else:
            curr = 0
        longest = max(longest, curr)
        d += timedelta(days=1)

    if today in dates:
        curr += 1
        longest = max(longest, curr)

    return (curr, longest)


def test_randomized_equivalence_with_reference_simulator() -> None:
    """Assert pure compute_streaks matches brute-force simulator over 300 random date sets."""
    rng = random.Random(1337)
    base_today = date(2026, 10, 20)

    for _ in range(300):
        span_days = rng.randint(5, 120)
        start = base_today - timedelta(days=span_days)
        prob = rng.uniform(0.1, 0.9)
        test_dates = {
            start + timedelta(days=i)
            for i in range(span_days + 1)
            if rng.random() < prob
        }
        freeze = rng.choice([True, False])

        result = compute_streaks(test_dates, base_today, freeze_enabled=freeze)
        expected_curr, expected_longest = naive_streak_simulator(
            test_dates, base_today, freeze_enabled=freeze
        )

        assert result.current == expected_curr
        assert result.longest == expected_longest
