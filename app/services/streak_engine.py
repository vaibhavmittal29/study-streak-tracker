"""Pure streak computation engine.

This module contains zero database calls, zero HTTP interactions, and zero
calls to datetime.now() or date.today(). It operates strictly on plain Python
values (set of dates, reference today date, and boolean flags).
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakResult:
    """Immutable result of streak computation."""

    current: int
    longest: int
    studied_today: bool
    at_risk: bool  # True when today has no study session yet and current > 0
    last_study_date: date | None
    frozen_dates: tuple[date, ...]  # Calendar dates where a freeze was consumed
    freeze_available_this_week: bool


def week_key(d: date) -> tuple[int, int]:
    """Return the ISO calendar year and week number for a date."""
    iso_year, iso_week, _ = d.isocalendar()
    return (iso_year, iso_week)


def compute_streaks(
    study_dates: set[date], today: date, freeze_enabled: bool = True
) -> StreakResult:
    """Compute current and longest streak from historical study dates.

    Rules:
    - Only dates <= today are considered (future dates ignored defensively).
    - Past days: evaluated consecutively from the earliest study date up to (today - 1).
    - Missed day with freeze: if freeze_enabled and current > 0 and no freeze was yet used
      in that day's ISO week, consumes that week's freeze. The streak survives with length
      unchanged.
    - Multiple sessions on the same date count as one study day (due to set input).
    - Today: evaluated last. If studied, current increments. If not studied today, current
      remains alive as of yesterday (today is pending until midnight).
    """
    # Defensive filtering: ignore future dates relative to reference today
    dates = {d for d in study_dates if d <= today}

    if not dates:
        return StreakResult(
            current=0,
            longest=0,
            studied_today=False,
            at_risk=False,
            last_study_date=None,
            frozen_dates=(),
            freeze_available_this_week=freeze_enabled,
        )

    current = 0
    longest = 0
    used_weeks: set[tuple[int, int]] = set()
    frozen: list[date] = []

    start_date = min(dates)
    day = start_date

    # Walk forward across completed days (up to today - 1 day)
    while day < today:
        if day in dates:
            current += 1
        elif freeze_enabled and current > 0 and week_key(day) not in used_weeks:
            used_weeks.add(week_key(day))
            frozen.append(day)
            # Streak survives, length is preserved
        else:
            current = 0

        longest = max(longest, current)
        day += timedelta(days=1)

    # Evaluate today
    studied_today = today in dates
    if studied_today:
        current += 1
        longest = max(longest, current)
    # else: today is pending; current remains as of yesterday (alive but at risk)

    at_risk = (not studied_today) and (current > 0)
    last_study_date = max(dates)
    freeze_available_this_week = freeze_enabled and (week_key(today) not in used_weeks)

    return StreakResult(
        current=current,
        longest=longest,
        studied_today=studied_today,
        at_risk=at_risk,
        last_study_date=last_study_date,
        frozen_dates=tuple(frozen),
        freeze_available_this_week=freeze_available_this_week,
    )
