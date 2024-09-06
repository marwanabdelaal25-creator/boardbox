"""Tests for boardbox.scale."""

import pytest

from boardbox.errors import ValidationError
from boardbox.scale import EditionScaler, ScaledIngredient, format_quantity, parse_quantity
from boardbox.storage import JsonStorage
from tests.helpers import make_game


def test_parse_quantity_fraction():
    assert parse_quantity("1/2") == 0.5


def test_parse_quantity_mixed():
    assert parse_quantity("1 1/2") == pytest.approx(1.5)


def test_parse_quantity_int():
    assert parse_quantity(4) == 4.0


def test_parse_quantity_empty():
    assert parse_quantity("") == 0.0


def test_parse_quantity_bad():
    assert parse_quantity("x") == 0.0


def test_format_quantity_int():
    assert format_quantity(2.0) == "2"


def test_format_quantity_fraction():
    assert "1/2" in format_quantity(0.5)


def test_format_quantity_mixed():
    assert "1" in format_quantity(1.5)


def test_format_quantity_no_nice():
    assert format_quantity(1.25, nice_fractions=False)


def test_scaler_ratio():
    s = EditionScaler()
    assert s.ratio(4, 8) == 2.0


def test_scaler_bad_year():
    s = EditionScaler()
    with pytest.raises(ValidationError):
        s.ratio(0, 4)
    with pytest.raises(ValidationError):
        s.ratio(4, 0)


def test_scale_mechanic_game_mechanic(sample_game):
    s = EditionScaler()
    ing = sample_game.mechanics[0]
    scaled = s.scale_mechanic(ing, 2.0)
    assert scaled.scaled_quantity == ing.quantity * 2


def test_scale_mechanic_dict():
    s = EditionScaler()
    scaled = s.scale_mechanic({"name": "flour", "quantity": "1/2", "unit": "cup"}, 2.0)
    assert scaled.scaled_quantity == 1.0


def test_scaled_mechanic_to_dict():
    si = ScaledIngredient("flour", 1.0, 2.0, "cup", 2.0)
    assert si.to_dict()["scaled_quantity"] == 2.0


def test_scale_game(populated_storage, sample_game):
    s = EditionScaler(populated_storage)
    scaled = s.scale_game(sample_game, 8)
    assert scaled["target_year"] == 8


def test_scale_game_from_dict(sample_game):
    s = EditionScaler()
    scaled = s.scale_game(sample_game.to_dict(), 2)
    assert scaled["ratio"] == 0.5


def test_scale_by_id(populated_storage, sample_game):
    s = EditionScaler(populated_storage)
    out = s.scale_by_id(sample_game.id, 2)
    assert out["game_id"] == sample_game.id


def test_scale_by_id_no_storage(sample_game):
    s = EditionScaler()
    with pytest.raises(ValidationError):
        s.scale_by_id(sample_game.id, 2)


def test_batch_scale(populated_storage, sample_game, sample_game2):
    s = EditionScaler(populated_storage)
    results = s.batch_scale([sample_game.id, sample_game2.id, "missing"], 6)
    assert len(results) == 2


def test_render_and_merge(populated_storage, sample_game):
    s = EditionScaler(populated_storage)
    scaled = s.scale_game(sample_game, 8)
    lines = s.render_wishlist_lines(scaled)
    assert lines
    merged = s.merge_scaled_mechanics([scaled, scaled])
    assert merged[0]["quantity"] > 0
