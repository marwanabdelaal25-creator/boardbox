"""Test builders for boardbox."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from boardbox.game import Game, MechanicLine, MechanicStep
from boardbox.mechanic import Ingredient, MechanicStub as RichMechanicStub
from boardbox.quantity import EditionGrade, Quantity
from boardbox.unit import Unit

# Recipebox-compat names used by ported tests
RecipeIngredient = MechanicLine
RecipeStep = MechanicStep
MechanicStub = MechanicLine


def make_ingredient(
    name: str = "flour",
    *,
    quantity: float = 2.0,
    unit: str = "cup",
    ingredient_id: str | None = None,
    mechanic_id: str | None = None,
    notes: str = "",
) -> MechanicLine:
    return MechanicLine(
        name=name,
        quantity=quantity,
        unit=unit,
        mechanic_id=mechanic_id or ingredient_id,
        notes=notes,
    )


make_mechanic_line = make_ingredient


def make_rich_ingredient(
    name: str = "flour",
    *,
    value: float = 2.0,
    unit: Unit = Unit.CUP,
    optional: bool = False,
    preparation: str = "",
) -> RichMechanicStub:
    return RichMechanicStub(
        name=name,
        quantity=EditionGrade(value, unit),
        optional=optional,
        preparation=preparation,
    )


make_rich_mechanic = make_rich_ingredient


def make_step(
    order: int = 1,
    text: str = "Mix mechanics.",
    *,
    duration_minutes: int | None = None,
) -> MechanicStep:
    return MechanicStep(order=order, text=text, duration_minutes=duration_minutes)


make_mechanic_step = make_step


def make_recipe(
    title: str = "Blue Train",
    *,
    recipe_id: str = "rec001",
    game_id: str | None = None,
    cuisine: str = "Blue Note",
    publisher_name: str | None = None,
    category: str = "LP",
    format: str | None = None,
    servings: int = 4,
    year: int | None = None,
    ingredients: list[MechanicLine] | None = None,
    mechanics: list[MechanicLine] | None = None,
    steps: list[MechanicStep] | None = None,
    componentlist: list[MechanicStep] | None = None,
    tag_ids: list[str] | None = None,
    archived: bool = False,
    favorite: bool = False,
    **extra: Any,
) -> Game:
    aid = game_id or recipe_id
    return Game(
        id=aid,
        title=title,
        publisher_name=publisher_name or cuisine,
        format=format or category,
        year=year if year is not None else servings,
        mechanics=mechanics or ingredients
        or [
            make_ingredient("Side A", quantity=1.0, unit="copy"),
            make_ingredient("Side B", quantity=1.0, unit="copy"),
        ],
        componentlist=componentlist or steps
        or [
            make_step(1, "Clean stylus.", duration_minutes=1),
            make_step(2, "Drop needle.", duration_minutes=45),
        ],
        tag_ids=tag_ids or ["jazz"],
        archived=archived,
        favorite=favorite,
        **extra,
    )


make_game = make_recipe


def make_recipe_dict(recipe: Game | None = None, **overrides: Any) -> dict[str, Any]:
    base = (recipe or make_recipe()).to_dict()
    base.update(overrides)
    return base


make_game_dict = make_recipe_dict


def make_night_plan_dict(
    *,
    plan_id: str = "plan001",
    week_start: str | None = None,
) -> dict[str, Any]:
    monday = date.today() - timedelta(days=date.today().weekday())
    return {
        "id": plan_id,
        "week_start": week_start or monday.isoformat(),
        "days": {
            "Monday": [{"game_id": "rec001", "meal": "dinner", "year": 4}],
            "Wednesday": [{"game_id": "rec001", "meal": "lunch", "year": 2}],
        },
        "notes": "Test week",
    }


make_campaign_dict = make_night_plan_dict


def make_pantry_item(
    name: str = "olive oil",
    *,
    item_id: str = "pan001",
    quantity: float = 500.0,
    unit: str = "ml",
    location: str = "bin",
) -> dict[str, Any]:
    return {
        "id": item_id,
        "name": name,
        "quantity": quantity,
        "unit": unit,
        "location": location,
    }


make_bin_item = make_pantry_item
make_bins_item = make_pantry_item


def make_catalog_ingredient(name: str = "garlic", aisle: str = "produce") -> Ingredient:
    return Ingredient(name=name, aisle=aisle, default_unit=Unit.CLOVE)


make_catalog_mechanic = make_catalog_ingredient


def make_mechanic(*args, **kwargs):
    if args and isinstance(args[0], int):
        return make_step(*args, **kwargs)
    if "quantity" in kwargs or (len(args) >= 2 and isinstance(args[1], (int, float))):
        return make_ingredient(*args, **kwargs)
    return make_rich_ingredient(*args, **kwargs)


def make_designer(name: str = "John Coltrane", *, designer_id: str = "art001"):
    from boardbox.designer import Designer

    return Designer.create(name=name, id=designer_id, country="US")
