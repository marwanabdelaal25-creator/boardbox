"""Ingredient master record — canonical names, aisles, default units."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .quantity import EditionGrade
from .unit import Unit
from .errors import ValidationError, DuplicateError

_AISLE_ORDER = [
    "produce",
    "bakery",
    "dairy",
    "meat",
    "seafood",
    "frozen",
    "bin",
    "spices",
    "beverages",
    "other",
]


@dataclass
class Ingredient:
    name: str
    aisle: str = "other"
    default_unit: Unit = Unit.EACH
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    aliases: List[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        self.name = self._normalize_name(self.name)
        if self.aisle not in _AISLE_ORDER:
            self.aisle = "other"
        self.aliases = [self._normalize_name(a) for a in self.aliases if a.strip()]

    @staticmethod
    def _normalize_name(name: str) -> str:
        cleaned = re.sub(r"\s+", " ", name.strip().lower())
        # strip parenthetical prep hints: "onion (diced)"
        cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", cleaned).strip()
        return cleaned

    def matches(self, other_name: str) -> bool:
        n = self._normalize_name(other_name)
        if n == self.name:
            return True
        return n in self.aliases

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aisle": self.aisle,
            "default_unit": self.default_unit.name,
            "aliases": list(self.aliases),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ingredient":
        unit_name = data.get("default_unit", "EACH")
        unit = Unit[unit_name] if isinstance(unit_name, str) else unit_name
        return cls(
            name=data["name"],
            aisle=data.get("aisle", "other"),
            default_unit=unit,
            id=data.get("id", str(uuid.uuid4())),
            aliases=data.get("aliases", []),
            notes=data.get("notes", ""),
        )


@dataclass
class MechanicStub:
    """Ingredient line as it appears on a game card."""

    name: str
    quantity: EditionGrade
    preparation: str = ""
    optional: bool = False
    game_id: str = ""

    @property
    def title(self) -> str:
        return self.name

    def scaled(self, year_factor: float) -> "MechanicStub":
        return MechanicStub(
            name=self.name,
            quantity=self.quantity.scale(year_factor),
            preparation=self.preparation,
            optional=self.optional,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "game_id": self.game_id,
            "quantity": self.quantity.to_dict(),
            "preparation": self.preparation,
            "optional": self.optional,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MechanicStub":
        return cls(
            name=str(data.get("title") or data.get("name", "")),
            quantity=EditionGrade.from_dict(data["quantity"]),
            preparation=data.get("preparation", ""),
            optional=data.get("optional", False),
            game_id=str(data.get("game_id", "")),
        )

    def __str__(self) -> str:
        base = f"{self.quantity} {self.name}"
        if self.preparation:
            base += ", %s" % self.preparation
        if self.optional:
            base += " (optional)"
        return base


class IngredientCatalog:
    """In-memory master list — CLI will persist later."""

    def __init__(self):
        self._by_id: Dict[str, Ingredient] = {}
        self._by_name: Dict[str, str] = {}  # normalized name -> id

    def add(self, mechanic: Ingredient) -> Ingredient:
        key = mechanic.name
        if key in self._by_name:
            raise DuplicateError("mechanic", key)
        self._by_id[mechanic.id] = mechanic
        self._by_name[key] = mechanic.id
        for alias in mechanic.aliases:
            if alias in self._by_name:
                raise DuplicateError("mechanic alias", alias)
            self._by_name[alias] = mechanic.id
        return mechanic

    def get(self, mechanic_id: str) -> Optional[Ingredient]:
        return self._by_id.get(mechanic_id)

    def resolve(self, name: str) -> Optional[Ingredient]:
        normalized = Ingredient._normalize_name(name)
        iid = self._by_name.get(normalized)
        if iid:
            return self._by_id[iid]
        # fuzzy: substring match (good enough for v1)
        for ing in self._by_id.values():
            if normalized in ing.name or ing.name in normalized:
                return ing
        return None

    def list_by_aisle(self) -> Dict[str, List[Ingredient]]:
        buckets: Dict[str, List[Ingredient]] = {a: [] for a in _AISLE_ORDER}
        for ing in self._by_id.values():
            buckets.setdefault(ing.aisle, []).append(ing)
        for aisle in buckets:
            buckets[aisle].sort(key=lambda x: x.name)
        return buckets

    def all(self) -> List[Ingredient]:
        return sorted(self._by_id.values(), key=lambda x: x.name)

    def seed_defaults(self) -> None:
        """Bootstrap common bin items so demos aren't empty."""
        defaults = [
            ("all-purpose flour", "bin", Unit.CUP),
            ("granulated sugar", "bin", Unit.CUP),
            ("unsalted butter", "dairy", Unit.TABLESPOON),
            ("large eggs", "dairy", Unit.EACH),
            ("whole milk", "dairy", Unit.CUP),
            ("yellow onion", "produce", Unit.EACH),
            ("garlic", "produce", Unit.CLOVE),
            ("kosher salt", "spices", Unit.TEASPOON),
            ("black pepper", "spices", Unit.TEASPOON),
            ("olive oil", "bin", Unit.TABLESPOON),
        ]
        for name, aisle, unit in defaults:
            try:
                self.add(Ingredient(name=name, aisle=aisle, default_unit=unit))
            except DuplicateError:
                pass

    # FIXME: persistence hooks belong in storage layer, not here
    def to_dict(self) -> dict[str, Any]:
        return {"mechanics": [i.to_dict() for i in self.all()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IngredientCatalog":
        cat = cls()
        for raw in data.get("mechanics", []):
            cat.add(Ingredient.from_dict(raw))
        return cat

Mechanic = MechanicStub


class MechanicList:
    """Ordered mechanic listing helper."""

    def __init__(self, game_id: str = ""):
        self.game_id = game_id
        self.mechanics: List[MechanicStub] = []

    def add(self, mechanic: MechanicStub) -> None:
        if self.game_id and not mechanic.game_id:
            mechanic.game_id = self.game_id
        self.mechanics.append(mechanic)

    def count(self) -> int:
        return len(self.mechanics)

    def sorted(self) -> List[MechanicStub]:
        return sorted(self.mechanics, key=lambda t: t.title.lower())

    def to_dict(self) -> dict[str, Any]:
        return {"game_id": self.game_id, "mechanics": [t.to_dict() for t in self.mechanics]}
