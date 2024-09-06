"""Tests for boardbox.nutrition."""

import pytest

from boardbox.errors import ValidationError
from boardbox.nutrition import ComplexityStore


def test_set_and_get(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_field(sample_game.id, "calories", 400)
    assert ns.get(sample_game.id)["calories"] == 400


def test_set_all_and_clear(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_all(sample_game.id, {"protein_g": 20, "bogus": 1})
    ns.clear(sample_game.id)
    assert ns.get(sample_game.id) == {}


def test_scale_and_per_serving(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_field(sample_game.id, "calories", 800)
    scaled = ns.scale_for_year(sample_game.id, 8)
    assert scaled["calories"] == 1600
    assert ns.per_serving(sample_game.id)["calories"] == 200


def test_validate_negative(populated_storage, sample_game):
    with pytest.raises(ValidationError):
        ComplexityStore(populated_storage).set_field(sample_game.id, "calories", -1)


def test_list_and_compare(populated_storage, sample_game, sample_game2):
    ns = ComplexityStore(populated_storage)
    ns.set_field(sample_game.id, "calories", 100)
    ns.set_field(sample_game2.id, "calories", 200)
    assert len(ns.list_with_nutrition()) >= 2
    assert len(ns.compare_games([sample_game.id, sample_game2.id])) == 2


def test_list_with_field_filter(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_field(sample_game.id, "protein_g", 10)
    rows = ns.list_with_nutrition(field="protein_g")
    assert rows


def test_render_studio_empty(populated_storage, sample_game2):
    ns = ComplexityStore(populated_storage)
    assert "(no nutrition data)" in ns.render_studio(sample_game2.id)


def test_scale_invalid_year(populated_storage):
    from unittest.mock import patch

    ns = ComplexityStore(populated_storage)
    game = populated_storage.get_game("rec001")
    game.year = 0
    with patch.object(populated_storage, "get_game", return_value=game):
        with pytest.raises(ValidationError):
            ns.scale_for_year("rec001", 2)


def test_set_all_skips_unknown_and_none(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    out = ns.set_all(sample_game.id, {"calories": 100, "bogus": 9, "protein_g": None})
    assert out.get("calories") == 100
    assert "bogus" not in out


def test_compare_missing_game(populated_storage):
    ns = ComplexityStore(populated_storage)
    assert ns.compare_games(["missing-id"]) == []


def test_render_and_daily(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_all(sample_game.id, {"calories": 300, "protein_g": 10})
    assert ns.render_studio(sample_game.id)
    assert ns.total_game(sample_game.id)["calories"] == 300
    populated_storage.create_session({"id": "mn1", "game_id": sample_game.id, "year": 2})
    assert ns.daily_totals_from_sessions(["mn1"])
    assert ns.validate({"calories": 1, "bad": 2})


def test_set_negative_raises(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    with pytest.raises(ValidationError):
        ns.set_field(sample_game.id, "calories", -1)


def test_validate_non_numeric():
    ns = ComplexityStore.__new__(ComplexityStore)
    errors = ns.validate({"calories": "not-a-number"})
    assert any("numeric" in e for e in errors)


def test_list_with_nutrition_field_filter(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_all(sample_game.id, {"calories": 200, "protein_g": 5})
    rows = ns.list_with_nutrition(field="protein_g")
    assert rows
    assert ns.list_with_nutrition(field="fiber_g") == []


def test_render_studio_all_macros(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_all(sample_game.id, {"calories": 100, "protein_g": 5, "carbs_g": 10, "fat_g": 3})
    studio = ns.render_studio(sample_game.id)
    assert "cal" in studio and "protein" in studio and "carbs" in studio and "fat" in studio


def test_daily_totals_empty_meal_ids(populated_storage, sample_game):
    ns = ComplexityStore(populated_storage)
    ns.set_all(sample_game.id, {"calories": 50})
    populated_storage.create_session({"id": "all1", "game_id": sample_game.id, "year": 1})
    totals = ns.daily_totals_from_sessions([])
    assert totals.get("calories", 0) > 0
