"""Scale game mechanic quantities by serving ratio.

Author: Marwan Helmy
"""

from __future__ import annotations

import copy
import enum
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Optional, Union

from .errors import ValidationError
from .game import Game, MechanicStub
from .storage import JsonStorage
from .validators import normalize_grade


class EditionGrade(str, enum.Enum):
    M = "M"
    NM = "NM"
    VG_PLUS = "VG+"
    VG = "VG"
    G = "G"
    F = "F"
    P = "P"


def parse_grade(raw: str) -> EditionGrade:
    normalized = normalize_grade(raw)
    for grade in EditionGrade:
        if grade.value == normalized:
            return grade
    raise ValidationError("unknown format grade", field="grade", value=raw)


FRACTION_PATTERN = re.compile(r"^(\d+)\s+(\d+)/(\d+)$")
MIXED_PATTERN = re.compile(r"^(\d+)\s+(\d+)/(\d+)$")


@dataclass
class ScaledMechanic:
    name: str
    original_quantity: float
    scaled_quantity: float
    unit: str
    ratio: float
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "original_quantity": self.original_quantity,
            "scaled_quantity": self.scaled_quantity,
            "unit": self.unit,
            "ratio": self.ratio,
            "notes": self.notes,
        }


def parse_quantity(value: Union[str, int, float]) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return 0.0
    if "/" in text and " " in text:
        parts = text.split()
        if len(parts) == 2:
            try:
                return float(Fraction(parts[0]) + Fraction(parts[1]))
            except (ValueError, ZeroDivisionError):
                pass
    if "/" in text:
        try:
            return float(Fraction(text))
        except (ValueError, ZeroDivisionError):
            pass
    try:
        return float(text)
    except ValueError:
        return 0.0  # TODO: raise on unparseable?


def format_quantity(qty: float, *, nice_fractions: bool = True) -> str:
    if qty == int(qty):
        return str(int(qty))
    if nice_fractions:
        frac = Fraction(qty).limit_denominator(16)
        if frac.denominator == 1:
            return str(frac.numerator)
        whole = int(qty)
        remainder = qty - whole
        if whole > 0 and remainder > 0:
            f = Fraction(remainder).limit_denominator(16)
            return f"{whole} {f.numerator}/{f.denominator}"
        return f"{frac.numerator}/{frac.denominator}"
    return f"{qty:.2f}".rstrip("0").rstrip(".")


class EditionScaler:
    def __init__(self, storage: Optional[JsonStorage] = None):
        self.storage = storage

    def ratio(self, original_year: int, target_year: int) -> float:
        if original_year < 1:
            raise ValidationError("original year must be >= 1")
        if target_year < 1:
            raise ValidationError("target year must be >= 1")
        return target_year / original_year

    def scale_mechanic(
        self,
        mechanic: MechanicStub | dict,
        ratio: float,
    ) -> ScaledMechanic:
        if isinstance(mechanic, MechanicStub):
            orig = mechanic.quantity
            name = mechanic.name
            unit = mechanic.unit
            notes = mechanic.notes
        else:
            orig = parse_quantity(mechanic.get("quantity", 1))
            name = str(mechanic.get("name", ""))
            unit = str(mechanic.get("unit", ""))
            notes = str(mechanic.get("notes", ""))
        scaled = round(orig * ratio, 4)
        return ScaledMechanic(
            name=name,
            original_quantity=orig,
            scaled_quantity=scaled,
            unit=unit,
            ratio=ratio,
            notes=notes,
        )

    def scale_game(
        self,
        game: Game | dict,
        target_year: int,
        *,
        as_dict: bool = True,
    ) -> dict[str, Any]:
        if isinstance(game, Game):
            r = game
        else:
            r = Game.from_dict(game)
        ratio = self.ratio(r.year, target_year)
        scaled_ings = []
        for ing in r.mechanics:
            s = self.scale_mechanic(ing, ratio)
            scaled_ings.append({
                "name": s.name,
                "quantity": s.scaled_quantity,
                "quantity_display": format_quantity(s.scaled_quantity),
                "unit": s.unit,
                "notes": s.notes,
            })
        out = {
            "game_id": r.id,
            "title": r.title,
            "original_year": r.year,
            "target_year": target_year,
            "ratio": ratio,
            "mechanics": scaled_ings,
            "componentlist": copy.deepcopy([s.to_dict() for s in r.componentlist]),
        }
        return out if as_dict else out  # FIXME: return typed object someday

    def scale_by_id(self, game_id: str, target_year: int) -> dict[str, Any]:
        if not self.storage:
            raise ValidationError("storage required for scale_by_id")
        game = self.storage.get_game(game_id)
        return self.scale_game(game, target_year)

    def batch_scale(
        self,
        game_ids: list[str],
        target_year: int,
    ) -> list[dict[str, Any]]:
        if not self.storage:
            raise ValidationError("storage required")
        results = []
        for rid in game_ids:
            try:
                results.append(self.scale_by_id(rid, target_year))
            except Exception:
                pass  # skip broken refs
        return results

    def render_wishlist_lines(self, scaled: dict[str, Any]) -> list[str]:
        lines = []
        for ing in scaled.get("mechanics", []):
            qty = ing.get("quantity_display") or format_quantity(ing.get("quantity", 0))
            unit = ing.get("unit", "")
            name = ing.get("name", "")
            if unit:
                lines.append(f"{qty} {unit} {name}".strip())
            else:
                lines.append(f"{qty} {name}".strip())
        return lines

    def merge_scaled_mechanics(
        self,
        scaled_games: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Combine same name+unit across multiple scaled games."""
        merged: dict[tuple[str, str], dict] = {}
        for game in scaled_games:
            for ing in game.get("mechanics", []):
                key = (ing.get("name", "").lower(), ing.get("unit", "").lower())
                if key not in merged:
                    merged[key] = {
                        "name": ing.get("name"),
                        "unit": ing.get("unit", ""),
                        "quantity": 0.0,
                    }
                merged[key]["quantity"] += float(ing.get("quantity", 0))
        out = []
        for row in merged.values():
            row["quantity_display"] = format_quantity(row["quantity"])
            out.append(row)
        out.sort(key=lambda r: r["name"].lower())
        return out


ScaledIngredient = ScaledMechanic
RecipeScaler = EditionScaler
