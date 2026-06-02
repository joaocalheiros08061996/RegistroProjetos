from datetime import datetime
from math import isclose

from domain.constants import WORKDAY_HOURS, WORKDAY_SECONDS
from domain.work_schedule import (
    planned_interval_to_hours,
    planned_interval_to_workdays,
    planned_progress,
)


def test_workday_has_eight_hours_and_forty_eight_minutes():
    assert WORKDAY_HOURS == 8.8
    assert WORKDAY_SECONDS == 31_680


def test_intraday_planning_preserves_literal_hours():
    start = datetime(2026, 1, 5, 8, 0)
    end = datetime(2026, 1, 5, 16, 0)

    assert isclose(planned_interval_to_hours(start, end), 8.0)
    assert isclose(planned_interval_to_workdays(start, end), 8.0 / WORKDAY_HOURS)


def test_multiday_planning_excludes_weekends():
    start = datetime(2026, 1, 2)
    end = datetime(2026, 1, 5)

    assert planned_interval_to_workdays(start, end) == 1.0
    assert planned_interval_to_hours(start, end) == WORKDAY_HOURS


def test_planned_progress_does_not_advance_during_weekend():
    start = datetime(2026, 1, 2)
    end = datetime(2026, 1, 6)

    saturday_progress = planned_progress(start, end, datetime(2026, 1, 3, 12))
    sunday_progress = planned_progress(start, end, datetime(2026, 1, 4, 12))

    assert saturday_progress == 0.5
    assert sunday_progress == saturday_progress
