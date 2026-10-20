"""Service computing weekly subject statistics and zero-filled time series."""

from collections import defaultdict
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import StudySession
from app.schemas import SubjectStat, TimeSeriesOut, TimeSeriesPoint, WeeklyStatsOut


def weekly_totals(db: Session, today: date) -> WeeklyStatsOut:
    """Calculate subject totals for the current ISO week (Monday to Sunday).

    Groups case-insensitively by subject_key while presenting the most recently
    logged display name for each subject.
    """
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Order newest date first, then newest id, so the first spelling seen is the latest
    sessions = (
        db.query(StudySession)
        .filter(StudySession.date >= week_start, StudySession.date <= week_end)
        .order_by(StudySession.date.desc(), StudySession.id.desc())
        .all()
    )

    if not sessions:
        return WeeklyStatsOut(
            week_start=week_start,
            week_end=week_end,
            total_minutes=0,
            subjects=[],
        )

    # Group by subject_key
    grouped: dict[str, dict] = {}
    for s in sessions:
        key = s.subject_key
        if key not in grouped:
            grouped[key] = {
                "display_name": s.subject,
                "minutes": 0,
                "sessions": 0,
            }
        grouped[key]["minutes"] += s.duration_minutes
        grouped[key]["sessions"] += 1

    subject_list = [
        SubjectStat(
            subject=data["display_name"],
            minutes=data["minutes"],
            sessions=data["sessions"],
        )
        for data in grouped.values()
    ]

    # Sort descending by study minutes
    subject_list.sort(key=lambda x: x.minutes, reverse=True)
    total_minutes = sum(item.minutes for item in subject_list)

    return WeeklyStatsOut(
        week_start=week_start,
        week_end=week_end,
        total_minutes=total_minutes,
        subjects=subject_list,
    )


def timeseries(
    db: Session,
    from_date: date,
    to_date: date,
    granularity: str = "day",
) -> TimeSeriesOut:
    """Generate a zero-filled time series of study minutes for charts."""
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'from' date ({from_date}) cannot be after 'to' date ({to_date})",
        )

    span_days = (to_date - from_date).days + 1
    if span_days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Time series range cannot exceed 366 days (requested: {span_days} days)",
        )

    if granularity not in {"day", "week"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Granularity must be either 'day' or 'week'",
        )

    sessions = (
        db.query(StudySession)
        .filter(StudySession.date >= from_date, StudySession.date <= to_date)
        .all()
    )

    points: list[TimeSeriesPoint] = []
    total_minutes = 0

    if granularity == "day":
        day_map: dict[date, list[int]] = defaultdict(list)
        for s in sessions:
            day_map[s.date].append(s.duration_minutes)

        curr = from_date
        while curr <= to_date:
            durations = day_map.get(curr, [])
            mins = sum(durations)
            total_minutes += mins
            points.append(
                TimeSeriesPoint(
                    date=curr.isoformat(),
                    minutes=mins,
                    sessions=len(durations),
                )
            )
            curr += timedelta(days=1)
    else:
        # Week granularity: bucket by Monday of each ISO week
        week_map: dict[date, list[int]] = defaultdict(list)
        for s in sessions:
            week_monday = s.date - timedelta(days=s.date.weekday())
            week_map[week_monday].append(s.duration_minutes)

        first_monday = from_date - timedelta(days=from_date.weekday())
        last_monday = to_date - timedelta(days=to_date.weekday())

        curr_week = first_monday
        while curr_week <= last_monday:
            durations = week_map.get(curr_week, [])
            mins = sum(durations)
            total_minutes += mins
            points.append(
                TimeSeriesPoint(
                    date=curr_week.isoformat(),
                    minutes=mins,
                    sessions=len(durations),
                )
            )
            curr_week += timedelta(days=7)

    return TimeSeriesOut(
        from_date=from_date,
        to_date=to_date,
        granularity=granularity,
        points=points,
        total_minutes=total_minutes,
    )
