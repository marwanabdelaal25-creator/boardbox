"""Game domain model and helpers.

Author: Marwan Helmy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = value.replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None


@dataclass
class MechanicLine:
    name: str
    quantity: float = 1.0
    unit: str = ""
    mechanic_id: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "mechanic_id": self.mechanic_id,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, row: dict) -> MechanicStub:
        return cls(
            name=str(row.get("name", "")),
            quantity=float(row.get("quantity", 1.0) or 1.0),
            unit=str(row.get("unit", "")),
            mechanic_id=row.get("mechanic_id"),
            notes=str(row.get("notes", "")),
        )


@dataclass
class MechanicStep:
    order: int
    text: str
    duration_minutes: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"order": self.order, "text": self.text}
        if self.duration_minutes is not None:
            out["duration_minutes"] = self.duration_minutes
        return out

    @classmethod
    def from_dict(cls, row: dict) -> MechanicStep:
        return cls(
            order=int(row.get("order", 0)),
            text=str(row.get("text", "")),
            duration_minutes=row.get("duration_minutes"),
        )


@dataclass
class Game:
    id: str
    title: str
    publisher_name: str = ""
    format: str = ""
    year: int = 4
    mechanics: list[MechanicLine] = field(default_factory=list)
    componentlist: list[MechanicStep] = field(default_factory=list)
    tag_ids: list[str] = field(default_factory=list)
    last_played_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    archived: bool = False
    favorite: bool = False
    rating: int = 0
    seasonal_tags: list[str] = field(default_factory=list)
    complexity: dict[str, Any] = field(default_factory=dict)
    source_url: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "publisher_name": self.publisher_name,
            "format": self.format,
            "year": self.year,
            "mechanics": [i.to_dict() for i in self.mechanics],
            "componentlist": [s.to_dict() for s in self.componentlist],
            "tag_ids": list(self.tag_ids),
            "last_played_at": self.last_played_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
            "favorite": self.favorite,
            "rating": self.rating,
            "seasonal_tags": list(self.seasonal_tags),
            "complexity": dict(self.complexity),
            "source_url": self.source_url,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, row: dict) -> Game:
        ings = [MechanicLine.from_dict(x) for x in row.get("mechanics", [])]
        componentlist = [MechanicStep.from_dict(x) for x in row.get("componentlist", [])]
        tags = row.get("tag_ids") or row.get("tags") or []
        return cls(
            id=str(row.get("id", "")),
            title=str(row.get("title", "")),
            publisher_name=str(row.get("publisher_name", "")),
            format=str(row.get("format", "")),
            year=int(row.get("year", 4) or 4),
            mechanics=ings,
            componentlist=componentlist,
            tag_ids=list(tags),
            last_played_at=row.get("last_played_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
            archived=bool(row.get("archived", False)),
            favorite=bool(row.get("favorite", False)),
            rating=int(row.get("rating", 0) or 0),
            seasonal_tags=list(row.get("seasonal_tags", [])),
            complexity=dict(row.get("complexity", {})),
            source_url=str(row.get("source_url", "")),
            notes=str(row.get("notes", "")),
        )

    def mechanic_names(self) -> list[str]:
        return [i.name for i in self.mechanics if i.name]

    def step_texts(self) -> list[str]:
        return [s.text for s in self.componentlist if s.text]


class GameCatalog:
    """In-memory game lookup for meal-plan wishlist aggregation."""

    def __init__(self, games: Optional[list[Game]] = None):
        self._by_id: dict[str, Game] = {}
        for game in games or []:
            self.add(game)

    def add(self, game: Game) -> None:
        self._by_id[game.id] = game

    def get(self, game_id: str) -> Optional[Game]:
        return self._by_id.get(game_id)

    def all(self) -> list[Game]:
        return list(self._by_id.values())

    def count(self) -> int:
        return len(self._by_id)


MechanicStub = MechanicLine
MechanicStepLine = MechanicStep
