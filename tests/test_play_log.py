"""Tests for boardbox.meal."""
from datetime import date, timedelta

import pytest

from boardbox.errors import ValidationError
from boardbox.meal import (
    Meal,
    MealLog,
    MealType,
    count_sessions_by_type,
    group_sessions_by_date,
    sessions_for_date,
    sessions_in_range,
    unique_game_ids,
)


def test_meal_create_and_studio():
    m = Meal("r1", date.today(), MealType.DINNER, notes="easy")
    assert "easy" in m.studio()
    assert m.slot_key


def test_meal_from_string_date_and_type():
    m = Meal("r1", "2024-06-01", "lunch")
    assert m.meal_type == MealType.LUNCH


def test_meal_empty_game_id_raises():
    with pytest.raises(ValidationError):
        Meal("  ", date.today(), MealType.DINNER)


def test_meal_bad_year_override():
    with pytest.raises(ValidationError):
        Meal("r1", date.today(), MealType.DINNER, year_override=0)


def test_meal_to_from_dict():
    m = Meal("r1", date.today(), MealType.BREAKFAST)
    restored = Meal.from_dict(m.to_dict())
    assert restored.game_id == "r1"


def test_sessions_for_date_and_range():
    today = date.today()
    sessions = [
        Meal("r1", today, MealType.BREAKFAST),
        Meal("r2", today, MealType.DINNER),
        Meal("r3", today + timedelta(days=1), MealType.LUNCH),
    ]
    assert len(sessions_for_date(sessions, today)) == 2
    assert len(sessions_in_range(sessions, today, today + timedelta(days=1))) == 3


def test_sessions_in_range_bad_dates():
    with pytest.raises(ValidationError):
        sessions_in_range([], date.today(), date.today() - timedelta(days=1))


def test_group_and_count():
    today = date.today()
    sessions = [Meal("r1", today, MealType.DINNER), Meal("r2", today, MealType.DINNER)]
    grouped = group_sessions_by_date(sessions)
    assert len(grouped[today]) == 2
    counts = count_sessions_by_type(sessions)
    assert counts["dinner"] == 2


def test_unique_game_ids():
    today = date.today()
    sessions = [Meal("r1", today, MealType.DINNER), Meal("r1", today, MealType.LUNCH)]
    assert unique_game_ids(sessions) == ["r1"]


def test_meal_log_ops():
    log = MealLog()
    m = Meal("r1", date.today(), MealType.DINNER)
    log.add(m)
    assert log.for_game("r1")
    assert log.remove(m.id)
    assert log.all() == []


def test_meal_log_upcoming():
    log = MealLog()
    log.add(Meal("r1", date.today() + timedelta(days=3), MealType.LUNCH))
    assert len(log.upcoming(date.today())) == 1


def test_meal_type_from_string():
    assert MealType.from_string("snack") == MealType.SNACK


def test_meal_log_to_from_dict():
    log = MealLog([Meal("r1", date.today(), MealType.DINNER)])
    restored = MealLog.from_dict(log.to_dict())
    assert len(restored.all()) == 1
