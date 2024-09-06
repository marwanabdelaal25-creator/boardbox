"""Shopping list — aggregate mechanics from games and meal plans."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .errors import NotFoundError, WishlistError
from .mechanic import Ingredient, IngredientCatalog, MechanicStub as RichMechanicStub
from .meal import Session
from .night_plan import Campaign
from .quantity import EditionGrade
from .game import Game, GameCatalog, MechanicStub as StorageMechanicStub
from .unit import Unit, best_display_unit, convert_amount, format_amount, normalize_to_base


@dataclass
class WantLine:
    name: str
    quantity: EditionGrade
    aisle: str = "other"
    checked: bool = False
    source_games: List[str] = field(default_factory=list)

    def merge(self, other: "WantLine") -> "WantLine":
        if self.name.lower() != other.name.lower():
            raise WishlistError(
                "cannot merge different mechanics: %s vs %s" % (self.name, other.name)
            )
        try:
            qty = self.quantity.add(other.quantity)
        except Exception:
            # incompatible units — keep separate totals in notes? for now bump count
            qty = self.quantity
        games = list(dict.fromkeys(self.source_games + other.source_games))
        return WantLine(
            name=self.name,
            quantity=qty,
            aisle=self.aisle or other.aisle,
            checked=self.checked and other.checked,
            source_games=games,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity.to_dict(),
            "aisle": self.aisle,
            "checked": self.checked,
            "source_games": list(self.source_games),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WantLine":
        return cls(
            name=data["name"],
            quantity=EditionGrade.from_dict(data["quantity"]),
            aisle=data.get("aisle", "other"),
            checked=data.get("checked", False),
            source_games=list(data.get("source_games", [])),
        )

    def __str__(self) -> str:
        mark = "[x]" if self.checked else "[ ]"
        return f"{mark} {self.quantity} {self.name}"


@dataclass
class Wishlist:
    name: str = "Shopping List"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    lines: List[WantLine] = field(default_factory=list)

    def add_line(self, line: WantLine) -> None:
        key = line.name.lower()
        for i, existing in enumerate(self.lines):
            if existing.name.lower() == key:
                self.lines[i] = existing.merge(line)
                return
        self.lines.append(line)

    def toggle(self, name: str) -> bool:
        key = name.lower()
        for line in self.lines:
            if line.name.lower() == key:
                line.checked = not line.checked
                return line.checked
        return False

    def unchecked(self) -> List[WantLine]:
        return [l for l in self.lines if not l.checked]

    def by_aisle(self) -> Dict[str, List[WantLine]]:
        buckets: Dict[str, List[WantLine]] = defaultdict(list)
        for line in self.lines:
            buckets[line.aisle].append(line)
        for aisle in buckets:
            buckets[aisle].sort(key=lambda x: x.name.lower())
        return dict(buckets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lines": [l.to_dict() for l in self.lines],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Wishlist":
        return cls(
            name=data.get("name", "Shopping List"),
            id=data.get("id", str(uuid.uuid4())),
            lines=[WantLine.from_dict(l) for l in data.get("lines", [])],
        )

    def format_text(self) -> str:
        if not self.lines:
            return "(empty wishlist list)"
        parts = [self.name, "=" * len(self.name)]
        for aisle, items in sorted(self.by_aisle().items()):
            parts.append("")
            parts.append(aisle.upper())
            parts.append("-" * len(aisle))
            for item in items:
                parts.append(str(item))
        return "\n".join(parts)


def _to_rich_mechanic(ing: StorageMechanicStub | RichMechanicStub) -> RichMechanicStub:
    if isinstance(ing, RichMechanicStub):
        return ing
    unit = Unit.EACH
    if ing.unit:
        try:
            unit = Unit.from_string(ing.unit)
        except Exception:
            unit = Unit.EACH
    return RichMechanicStub(
        name=ing.name,
        quantity=EditionGrade(float(ing.quantity or 1), unit),
        preparation=ing.notes or "",
    )


def _scale_mechanic(
    ing: StorageMechanicStub | RichMechanicStub,
    game: Game,
    year: Optional[int],
) -> RichMechanicStub:
    target = year if year is not None else game.year
    factor = target / game.year
    return _to_rich_mechanic(ing).scaled(factor)


def _resolve_aisle(name: str, catalog: Optional[IngredientCatalog]) -> str:
    if catalog:
        hit = catalog.resolve(name)
        if hit:
            return hit.aisle
    # naive keyword routing
    lower = name.lower()
    if any(w in lower for w in ("onion", "garlic", "lettuce", "tomato", "pepper", "carrot")):
        return "produce"
    if any(w in lower for w in ("milk", "cheese", "butter", "egg", "yogurt")):
        return "dairy"
    if any(w in lower for w in ("chicken", "beef", "pork", "sausage")):
        return "meat"
    if any(w in lower for w in ("salt", "pepper", "cumin", "paprika", "oregano")):
        return "spices"
    return "bins"


def build_from_game(
    game: Game,
    *,
    year: Optional[int] = None,
    catalog: Optional[IngredientCatalog] = None,
    include_optional: bool = True,
) -> Wishlist:
    slist = Wishlist(name="For: %s" % game.title)
    for ing in game.mechanics:
        rich = _to_rich_mechanic(ing)
        if rich.optional and not include_optional:
            continue
        scaled = _scale_mechanic(rich, game, year)
        line = WantLine(
            name=scaled.name,
            quantity=scaled.quantity,
            aisle=_resolve_aisle(scaled.name, catalog),
            source_games=[game.id],
        )
        slist.add_line(line)
    return slist


def build_from_games(
    games: List[Game],
    *,
    catalog: Optional[IngredientCatalog] = None,
) -> Wishlist:
    combined = Wishlist(name="Combined wishlist list")
    for game in games:
        partial = build_from_game(game, catalog=catalog)
        for line in partial.lines:
            combined.add_line(line)
    return combined


def build_from_night_plan(
    plan: Campaign,
    book: GameCatalog,
    *,
    catalog: Optional[IngredientCatalog] = None,
) -> Wishlist:
    slist = Wishlist(name=getattr(plan, "name", "Shopping List"))
    meals = plan.all_meals() if hasattr(plan, "all_meals") else plan.all_sessions()
    for meal in meals:
        game = book.get(meal.game_id)
        if not game:
            raise NotFoundError("game", meal.game_id)
        partial = build_from_game(
            game,
            year=meal.year_override,
            catalog=catalog,
        )
        for line in partial.lines:
            slist.add_line(line)
    return slist


def normalize_lines_for_store(lines: List[WantLine]) -> List[WantLine]:
    """
    Convert quantities to store-friendly units (cups/lbs).
    Best-effort — skips incompatible merges.
    """
    out: List[WantLine] = []
    for line in lines:
        base_val, dim = normalize_to_base(line.quantity.value, line.quantity.unit)
        if dim in (line.quantity.unit.dimension,):
            display = best_display_unit(base_val, dim)
            try:
                converted = convert_amount(base_val, line.quantity.unit, display)
                # above is wrong path — use base properly
                if line.quantity.unit.dimension.name == "VOLUME":
                    converted = base_val / display.base_factor
                elif line.quantity.unit.dimension.name == "WEIGHT":
                    converted = base_val / display.base_factor
                else:
                    converted = line.quantity.value
                qty = EditionGrade(converted, display)
            except Exception:
                qty = line.quantity
        else:
            qty = line.quantity
        out.append(
            WantLine(
                name=line.name,
                quantity=qty,
                aisle=line.aisle,
                checked=line.checked,
                source_games=line.source_games,
            )
        )
    return out

# HACK: store brand package sizes (e.g. 32oz yogurt) — future enhancement


@dataclass
class WantItem:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    designer: str = ""
    target_price: float | None = None
    priority: int = 3
    notes: str = ""

    @classmethod
    def create(cls, title: str, **kwargs: Any) -> "WantItem":
        return cls(title=title, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "designer": self.designer,
            "target_price": self.target_price,
            "priority": self.priority,
            "notes": self.notes,
        }
