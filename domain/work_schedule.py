from __future__ import annotations

from datetime import date, datetime, time, timedelta

from .constants import WORKDAY_HOURS, WORKDAY_SECONDS

CALENDAR_DAY_SECONDS = 86_400


def worked_hours_to_workdays(hours: float) -> float:
    return max(0.0, float(hours)) / WORKDAY_HOURS


def _day_start(day: date, template: datetime) -> datetime:
    return datetime.combine(day, time.min, tzinfo=template.tzinfo)


def _weekday_calendar_days_between(start: datetime, end: datetime) -> float:
    if end <= start:
        return 0.0

    total_days = 0.0
    current_day = start.date()
    while current_day <= end.date():
        if current_day.weekday() < 5:
            day_start = _day_start(current_day, start)
            day_end = day_start + timedelta(days=1)
            overlap_start = max(start, day_start)
            overlap_end = min(end, day_end)
            if overlap_end > overlap_start:
                total_days += (
                    overlap_end - overlap_start
                ).total_seconds() / CALENDAR_DAY_SECONDS
        current_day += timedelta(days=1)

    return total_days


def planned_interval_to_workdays(start: datetime, end: datetime) -> float:
    if end <= start:
        return 0.0
    if start.date() == end.date():
        return (end - start).total_seconds() / WORKDAY_SECONDS
    return _weekday_calendar_days_between(start, end)


def planned_interval_to_hours(start: datetime, end: datetime) -> float:
    return planned_interval_to_workdays(start, end) * WORKDAY_HOURS


def planned_progress(start: datetime, end: datetime, reference: datetime) -> float:
    if end <= start or reference <= start:
        return 0.0
    if reference >= end:
        return 1.0

    if start.date() == end.date():
        total_seconds = (end - start).total_seconds()
        elapsed_seconds = (reference - start).total_seconds()
        return max(0.0, min(1.0, elapsed_seconds / total_seconds))

    planned_days = _weekday_calendar_days_between(start, end)
    if planned_days <= 0:
        return 0.0

    elapsed_days = _weekday_calendar_days_between(start, reference)
    return max(0.0, min(1.0, elapsed_days / planned_days))
