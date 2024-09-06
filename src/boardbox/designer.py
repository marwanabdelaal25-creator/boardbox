"""Designer entity — performers, bands, roles."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any
import uuid

from boardbox.validators import validate_title, validate_id, validate_optional_url, validate_metadata


def validate_designer_name(name: str) -> str:
    return validate_title(name)


@dataclass
class Designer:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sort_name: str | None = None
    country: str | None = None
    genres: list[str] = field(default_factory=list)
    bgg_designer_id: int | None = None
    tabletop_designer_id: str | None = None
    photo_url: str | None = None
    bio: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Designer":
        aid = kwargs.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(name=name, id=aid, **kwargs)

    def __post_init__(self) -> None:
        self.name = validate_designer_name(self.name)
        self.id = validate_id(self.id)
        self.photo_url = validate_optional_url(self.photo_url)
        self.metadata = validate_metadata(self.metadata)
        if not self.sort_name:
            self.sort_name = self._default_sort_name(self.name)

    @staticmethod
    def _default_sort_name(name: str) -> str:
        if name.lower().startswith("the "):
            return name[4:] + ", The"
        return name

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Designer":
        return cls(
            name=data["name"],
            id=data.get("id", uuid.uuid4().hex[:12]),
            sort_name=data.get("sort_name"),
            country=data.get("country"),
            genres=list(data.get("genres") or []),
            bgg_designer_id=data.get("bgg_designer_id"),
            tabletop_designer_id=data.get("tabletop_designer_id"),
            photo_url=data.get("photo_url"),
            bio=data.get("bio", ""),
            metadata=dict(data.get("metadata") or {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )


class DesignerRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, Designer] = {}
        self._by_name: dict[str, str] = {}

    def add(self, designer: Designer) -> Designer:
        self._by_id[designer.id] = designer
        self._by_name[designer.name.lower()] = designer.id
        return designer

    def get(self, designer_id: str) -> Designer | None:
        return self._by_id.get(designer_id)

    def find_by_name(self, name: str) -> Designer | None:
        aid = self._by_name.get(name.lower())
        return self._by_id.get(aid) if aid else None

    def all(self) -> list[Designer]:
        return sorted(self._by_id.values(), key=lambda a: (a.sort_name or a.name).lower())

    def resolve_or_create(self, name: str) -> Designer:
        existing = self.find_by_name(name)
        if existing:
            return existing
        return self.add(Designer.create(name))

    @classmethod
    def from_dict_list(cls, rows: list[dict[str, Any]]) -> "DesignerRegistry":
        reg = cls()
        for row in rows:
            reg.add(Designer.from_dict(row))
        return reg
