"""Unit enum and conversion helpers for home-cooking quantities."""

from __future__ import annotations

import enum
from typing import Dict, Optional, Tuple

from .errors import ConversionError

# I tried metric-only once, gave up — American games are stubborn.


class UnitDimension(enum.Enum):
    VOLUME = "volume"
    WEIGHT = "weight"
    COUNT = "count"
    OTHER = "other"


class Unit(enum.Enum):
    # volume — imperial leaning because that's what my grandma's cards use
    TEASPOON = ("tsp", UnitDimension.VOLUME, 4.92892)
    TABLESPOON = ("tbsp", UnitDimension.VOLUME, 14.7868)
    FLUID_OUNCE = ("fl oz", UnitDimension.VOLUME, 29.5735)
    CUP = ("cup", UnitDimension.VOLUME, 236.588)
    PINT = ("pint", UnitDimension.VOLUME, 473.176)
    QUART = ("quart", UnitDimension.VOLUME, 946.353)
    GALLON = ("gallon", UnitDimension.VOLUME, 3785.41)
    MILLILITER = ("ml", UnitDimension.VOLUME, 1.0)
    LITER = ("l", UnitDimension.VOLUME, 1000.0)

    # weight
    OUNCE = ("oz", UnitDimension.WEIGHT, 28.3495)
    POUND = ("lb", UnitDimension.WEIGHT, 453.592)
    GRAM = ("g", UnitDimension.WEIGHT, 1.0)
    KILOGRAM = ("kg", UnitDimension.WEIGHT, 1000.0)

    # count-ish
    EACH = ("each", UnitDimension.COUNT, 1.0)
    CLOVE = ("clove", UnitDimension.COUNT, 1.0)
    SLICE = ("slice", UnitDimension.COUNT, 1.0)
    PINCH = ("pinch", UnitDimension.OTHER, 1.0)
    DASH = ("dash", UnitDimension.OTHER, 1.0)
    BUNCH = ("bunch", UnitDimension.OTHER, 1.0)
    CAN = ("can", UnitDimension.OTHER, 1.0)
    PACKAGE = ("pkg", UnitDimension.OTHER, 1.0)

    def __init__(self, abbrev: str, dimension: UnitDimension, base_factor: float):
        self.abbrev = abbrev
        self.dimension = dimension
        self.base_factor = base_factor

    @classmethod
    def from_string(cls, raw: str) -> "Unit":
        normalized = raw.strip().lower().replace(".", "")
        aliases: Dict[str, Unit] = {}
        for u in cls:
            aliases[u.abbrev.lower()] = u
            aliases[u.name.lower()] = u
        # common kitchen slang
        extras = {
            "c": Unit.CUP,
            "cups": Unit.CUP,
            "t": Unit.TEASPOON,
            "tsp.": Unit.TEASPOON,
            "tsps": Unit.TEASPOON,
            "tbsp.": Unit.TABLESPOON,
            "tbs": Unit.TABLESPOON,
            "tablespoons": Unit.TABLESPOON,
            "teaspoons": Unit.TEASPOON,
            "lbs": Unit.POUND,
            "pounds": Unit.POUND,
            "ounces": Unit.OUNCE,
            "grams": Unit.GRAM,
            "g.": Unit.GRAM,
            "kilograms": Unit.KILOGRAM,
            "milliliters": Unit.MILLILITER,
            "liters": Unit.LITER,
            "ea": Unit.EACH,
            "whole": Unit.EACH,
            "head": Unit.EACH,
            "stick": Unit.EACH,  # butter — FIXME: should be weight-ish
        }
        aliases.update(extras)
        hit = aliases.get(normalized)
        if not hit:
            raise ConversionError(raw, "?", reason="unknown unit abbreviation")
        return hit

    def compatible_with(self, other: "Unit") -> bool:
        if self.dimension == other.dimension:
            return True
        # pinch/dash don't convert cleanly — treat as incompatible
        if self.dimension == UnitDimension.OTHER or other.dimension == UnitDimension.OTHER:
            return self == other
        return False


def convert_amount(value: float, from_unit: Unit, to_unit: Unit) -> float:
    if from_unit == to_unit:
        return value
    if not from_unit.compatible_with(to_unit):
        raise ConversionError(from_unit.abbrev, to_unit.abbrev, reason="incompatible dimensions")
    if from_unit.dimension == UnitDimension.COUNT:
        if value != int(value):
            # HACK: allow half-clove? no. just round for wishlist lists.
            value = round(value, 2)
        return float(int(value) if value == int(value) else value)
    base = value * from_unit.base_factor
    return base / to_unit.base_factor


def normalize_to_base(value: float, unit: Unit) -> Tuple[float, UnitDimension]:
    """Return value expressed in ml (volume) or g (weight) where possible."""
    if unit.dimension == UnitDimension.VOLUME:
        ml = value * unit.base_factor
        return ml, UnitDimension.VOLUME
    if unit.dimension == UnitDimension.WEIGHT:
        grams = value * unit.base_factor
        return grams, UnitDimension.WEIGHT
    return value, unit.dimension


def best_display_unit(value: float, dimension: UnitDimension) -> Unit:
    """Pick a human-friendly unit for printing wishlist lists."""
    if dimension == UnitDimension.VOLUME:
        if value >= 1000:
            return Unit.LITER
        if value >= 236:
            return Unit.CUP
        if value >= 14:
            return Unit.TABLESPOON
        return Unit.TEASPOON
    if dimension == UnitDimension.WEIGHT:
        if value >= 1000:
            return Unit.KILOGRAM
        if value >= 453:
            return Unit.POUND
        if value >= 28:
            return Unit.OUNCE
        return Unit.GRAM
    return Unit.EACH


def format_amount(value: float, unit: Unit, *, precision: int = 2) -> str:
    if value == int(value):
        return "%d %s" % (int(value), unit.abbrev)
    rounded = round(value, precision)
    return "{0:.2f} {1}".format(rounded, unit.abbrev)


# TODO: density table for volume<->weight (flour vs sugar) — out of scope for v1
_DENSITY_G_PER_ML: Dict[str, float] = {
    "water": 1.0,
    "milk": 1.03,
    "flour": 0.53,
    "sugar": 0.85,
    "butter": 0.96,
}


def convert_volume_to_weight(
    value: float,
    volume_unit: Unit,
    mechanic_key: str,
    target_weight: Unit = Unit.GRAM,
) -> float:
    """Rough conversion using mechanic density — good enough for grocery runs."""
    if volume_unit.dimension != UnitDimension.VOLUME:
        raise ConversionError(volume_unit.abbrev, target_weight.abbrev, reason="source not volume")
    ml, _ = normalize_to_base(value, volume_unit)
    density = _DENSITY_G_PER_ML.get(mechanic_key.lower(), 1.0)
    grams = ml * density
    return convert_amount(grams, Unit.GRAM, target_weight)
