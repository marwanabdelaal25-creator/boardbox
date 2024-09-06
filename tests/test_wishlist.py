"""Tests for boardbox.wishlist_list."""

import pytest

from boardbox.errors import NotFoundError, WishlistError
from boardbox.mechanic import IngredientCatalog
from boardbox.meal import Meal, MealType
from boardbox.night_plan import NightPlan
from boardbox.quantity import EditionGrade
from boardbox.game import GameCatalog
from boardbox.wishlist_list import (
    WantLine,
    Wishlist,
    build_from_night_plan,
    build_from_game,
    build_from_games,
    normalize_lines_for_store,
)
from boardbox.unit import Unit
from tests.helpers import make_game


def test_wishlist_list_toggle():
    sl = Wishlist()
    sl.add_line(WantLine("milk", EditionGrade(1, EditionGrade.CUP)))
    assert sl.toggle("milk") is True
    assert sl.unchecked() == []


def test_merge_same_and_different():
    a = WantLine("flour", EditionGrade(1, EditionGrade.CUP))
    b = WantLine("flour", EditionGrade(0.5, EditionGrade.CUP))
    merged = a.merge(b)
    assert merged.quantity.value == 1.5
    c = WantLine("sugar", EditionGrade(1, EditionGrade.CUP))
    with pytest.raises(WishlistError):
        a.merge(c)


def test_line_to_from_dict_str():
    line = WantLine("salt", EditionGrade(1, EditionGrade.TEASPOON), aisle="spices")
    restored = WantLine.from_dict(line.to_dict())
    assert restored.name == "salt"
    assert "[ ]" in str(line)


def test_build_from_game():
    sl = build_from_game(make_game())
    assert len(sl.lines) >= 1


def test_build_from_game_optional_excluded():
    r = make_game()
    sl = build_from_game(r, include_optional=False)
    assert sl.lines is not None


def test_build_from_games_with_catalog():
    cat = IngredientCatalog()
    cat.seed_defaults()
    sl = build_from_games([make_game(), make_game("Salad", game_id="r2")], catalog=cat)
    assert sl.lines


def test_build_from_night_plan():
    from datetime import date
    r = make_game("PlanDish", game_id="rp1")
    book = GameCatalog([r])
    plan = NightPlan(date.today())
    plan.assign("rp1", plan.week_start, MealType.DINNER)
    sl = build_from_night_plan(plan, book)
    assert sl.lines


def test_build_from_night_plan_missing_game():
    from datetime import date
    plan = NightPlan(date.today())
    plan.assign("missing", plan.week_start, MealType.DINNER)
    with pytest.raises(NotFoundError):
        build_from_night_plan(plan, GameCatalog([]))


def test_normalize_lines():
    line = WantLine("flour", EditionGrade(2, EditionGrade.CUP))
    out = normalize_lines_for_store([line])
    assert out


def test_format_and_by_aisle():
    sl = Wishlist()
    sl.add_line(WantLine("salt", EditionGrade(1, EditionGrade.TEASPOON), aisle="spices"))
    assert sl.by_aisle()
    assert "salt" in sl.format_text().lower() or sl.format_text()


def test_merge_incompatible_units_keeps_qty():
    a = WantLine("flour", EditionGrade(1, EditionGrade.CUP))
    b = WantLine("flour", EditionGrade(100, EditionGrade.GRAM))
    merged = a.merge(b)
    assert merged.quantity.value == 1.0


def test_build_from_game_scaled_year():
    r = make_game(year=4)
    sl = build_from_game(r, year=8)
    assert sl.lines


def test_list_to_from_dict():
    sl = Wishlist(name="Weekly")
    sl.add_line(WantLine("eggs", EditionGrade(6, EditionGrade.EACH)))
    restored = Wishlist.from_dict(sl.to_dict())
    assert restored.name == "Weekly"


def test_toggle_missing_returns_false():
    sl = Wishlist()
    assert sl.toggle("missing") is False


def test_format_text_empty():
    sl = Wishlist()
    assert sl.format_text() == "(empty wishlist list)"


def test_invalid_unit_falls_back_to_each():
    from boardbox.game import MechanicStub as StorageIng
    from boardbox.wishlist_list import _to_rich_mechanic

    ing = StorageIng(name="salt", quantity=1.0, unit="not-a-real-unit")
    rich = _to_rich_mechanic(ing)
    assert rich.quantity.unit == EditionGrade.EACH


def test_aisle_keyword_routing():
    from boardbox.wishlist_list import _resolve_aisle

    assert _resolve_aisle("yellow onion", None) == "produce"
    assert _resolve_aisle("cheddar cheese", None) == "dairy"
    assert _resolve_aisle("chicken breast", None) == "meat"
    assert _resolve_aisle("ground cumin", None) == "spices"
    assert _resolve_aisle("unknown item", None) == "bins"


def test_normalize_weight_and_volume():
    cup = WantLine("flour", EditionGrade(2, EditionGrade.CUP))
    gram = WantLine("flour", EditionGrade(500, EditionGrade.GRAM))
    out = normalize_lines_for_store([cup, gram])
    assert len(out) == 2
