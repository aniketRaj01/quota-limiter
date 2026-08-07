from __future__ import annotations

from datetime import date

from service.services.period import current_period_start, next_reset_at


def test_lands_exactly_on_anchor_day():
    assert current_period_start(15, date(2026, 3, 15)) == date(2026, 3, 15)


def test_day_before_anchor_still_previous_period():
    assert current_period_start(15, date(2026, 3, 14)) == date(2026, 2, 15)


def test_day_after_anchor_rolls_to_current_month():
    assert current_period_start(15, date(2026, 3, 16)) == date(2026, 3, 15)


def test_anchor_beyond_month_length_clamps_in_current_month():
    # April has 30 days; anchor 31 clamps to April 30, and today (4/30) has reached it.
    assert current_period_start(31, date(2026, 4, 30)) == date(2026, 4, 30)


def test_anchor_beyond_month_length_falls_back_to_clamped_previous_month():
    # April 15 hasn't reached April's clamped anchor (30) yet, so falls back to
    # March, whose own clamp for anchor 31 is 31 (March has 31 days).
    assert current_period_start(31, date(2026, 4, 15)) == date(2026, 3, 31)


def test_feb_29_anchor_in_non_leap_year_clamps_to_28():
    # 2027 is not a leap year; anchor 29 in Feb clamps to Feb 28, which hasn't been
    # reached by Feb 15, so falls back to January's unclamped anchor day 29.
    assert current_period_start(29, date(2027, 2, 15)) == date(2027, 1, 29)


def test_current_period_start_rolls_back_across_year_boundary():
    assert current_period_start(15, date(2026, 1, 10)) == date(2025, 12, 15)


def test_next_reset_at_normal_month():
    assert next_reset_at(date(2026, 3, 15), 15) == "2026-04-15T00:00:00Z"


def test_next_reset_at_wraps_year_boundary():
    assert next_reset_at(date(2025, 12, 15), 15) == "2026-01-15T00:00:00Z"


def test_next_reset_at_clamps_for_shorter_next_month():
    assert next_reset_at(date(2026, 1, 31), 31) == "2026-02-28T00:00:00Z"
