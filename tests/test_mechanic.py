"""Tests for boardbox.mechanic."""
import pytest

from boardbox.errors import DuplicateError
from boardbox.mechanic import Ingredient, IngredientCatalog, MechanicStub
from boardbox.quantity import EditionGrade
from boardbox.unit import Unit
from tests.helpers import make_catalog_mechanic, make_rich_mechanic


def test_mechanic_normalize():
    ing = Ingredient(name="  Onion (diced)  ")
    assert "onion" in ing.name


def test_mechanic_bad_aisle_defaults_other():
    ing = Ingredient(name="salt", aisle="unknown-aisle")
    assert ing.aisle == "other"


def test_mechanic_matches_and_aliases():
    ing = Ingredient(name="garlic", aliases=["Garlic Cloves"])
    assert ing.matches("Garlic Cloves")
    assert not ing.matches("onion")


def test_mechanic_to_from_dict():
    ing = make_catalog_mechanic("basil", aisle="produce")
    restored = Ingredient.from_dict(ing.to_dict())
    assert restored.name == ing.name


def test_rich_mechanic_scaled():
    ri = make_rich_mechanic()
    assert ri.scaled(2).quantity.value == 4


def test_rich_mechanic_to_dict_str():
    ri = make_rich_mechanic("flour", preparation="sifted", optional=True)
    d = ri.to_dict()
    assert d["preparation"] == "sifted"
    assert "(optional)" in str(MechanicStub.from_dict(d))


def test_rich_mechanic_from_dict():
    data = {"name": "sugar", "quantity": {"value": 1, "unit": "CUP"}, "optional": False}
    ri = MechanicStub.from_dict(data)
    assert ri.name == "sugar"


def test_catalog_duplicate():
    cat = IngredientCatalog()
    cat.add(make_catalog_mechanic("garlic"))
    with pytest.raises(DuplicateError):
        cat.add(make_catalog_mechanic("garlic"))


def test_catalog_duplicate_alias():
    cat = IngredientCatalog()
    cat.add(Ingredient(name="tomato", aliases=["roma"]))
    with pytest.raises(DuplicateError):
        cat.add(Ingredient(name="roma"))


def test_catalog_resolve_and_get():
    cat = IngredientCatalog()
    ing = cat.add(make_catalog_mechanic("cilantro"))
    assert cat.get(ing.id) is ing
    assert cat.resolve("cilantro") is ing
    assert cat.resolve("partial cilantro match") is ing


def test_catalog_list_by_aisle():
    cat = IngredientCatalog()
    cat.add(make_catalog_mechanic("apple", aisle="produce"))
    cat.add(make_catalog_mechanic("flour", aisle="bins"))
    buckets = cat.list_by_aisle()
    assert any(i.name == "apple" for i in buckets["produce"])


def test_catalog_seed_defaults():
    cat = IngredientCatalog()
    cat.seed_defaults()
    assert len(cat.all()) >= 5
    cat.seed_defaults()  # idempotent


def test_catalog_to_from_dict():
    cat = IngredientCatalog()
    cat.add(make_catalog_mechanic("rice"))
    restored = IngredientCatalog.from_dict(cat.to_dict())
    assert len(restored.all()) == 1
