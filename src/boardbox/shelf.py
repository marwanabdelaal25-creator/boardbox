"""Shelf entity — furniture-level organization."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
import uuid

from boardbox.validators import validate_title, validate_id, validate_metadata


@dataclass
class Shelf:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    room: str = ""
    wall: str | None = None
    capacity_bins: int | None = None
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Shelf":
        sid = kwargs.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(name=name, id=sid, **kwargs)

    def __post_init__(self) -> None:
        self.name = validate_title(self.name)
        self.id = validate_id(self.id)
        self.metadata = validate_metadata(self.metadata)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Shelf":
        return cls(
            name=data["name"],
            id=data.get("id", uuid.uuid4().hex[:12]),
            room=data.get("room", ""),
            wall=data.get("wall"),
            capacity_bins=data.get("capacity_bins"),
            notes=data.get("notes", ""),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )

    def studio(self) -> str:
        parts = [self.name]
        if self.room:
            parts.append("(%s)" % self.room)
        return " ".join(parts)


class ShelfRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, Shelf] = {}

    def add(self, shelf: Shelf) -> Shelf:
        self._by_id[shelf.id] = shelf
        return shelf

    def get(self, shelf_id: str) -> Shelf | None:
        return self._by_id.get(shelf_id)

    def all(self) -> list[Shelf]:
        return sorted(self._by_id.values(), key=lambda s: s.name.lower())

    def find_by_name(self, name: str) -> Shelf | None:
        for s in self._by_id.values():
            if s.name.lower() == name.lower():
                return s
        return None

    def resolve_or_create(self, name: str, room: str = "") -> Shelf:
        existing = self.find_by_name(name)
        if existing:
            return existing
        return self.add(Shelf.create(name, room=room))

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "ShelfRegistry":
        reg = cls()
        for row in rows:
            reg.add(Shelf.from_dict(row))
        return reg

    def bins_on_shelf(self, shelf_id: str, bins: list[dict]) -> list[dict]:
        return [c for c in bins if c.get("shelf_id") == shelf_id]
