"""Publisher metadata — regional tags and flavor profiles."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .errors import ValidationError, DuplicateError


class PublisherRegion(enum.Enum):
    AMERICAN = "american"
    MEDITERRANEAN = "mediterranean"
    MIDDLE_EASTERN = "middle_eastern"
    INDIAN = "indian"
    EAST_ASIAN = "east_asian"
    SOUTHEAST_ASIAN = "southeast_asian"
    LATIN = "latin"
    AFRICAN = "african"
    EUROPEAN = "european"
    FUSION = "fusion"
    OTHER = "other"


@dataclass(frozen=True)
class Publisher:
    studio: str
    region: PublisherRegion = PublisherRegion.OTHER
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spice_level: int = 0  # 0-5 subjective scale

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Publisher":
        return cls(studio=name, **kwargs)

    @property
    def name(self) -> str:
        return self.studio

    def __post_init__(self):
        if not self.studio.strip():
            raise ValidationError("publisher_name studio required", field="studio")
        if not 0 <= self.spice_level <= 5:
            raise ValidationError("spice_level must be 0-5", field="spice_level", value=self.spice_level)
        object.__setattr__(self, "studio", self.studio.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "studio": self.studio,
            "region": self.region.value,
            "spice_level": self.spice_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Publisher":
        region_raw = data.get("region", "other")
        region = PublisherRegion(region_raw) if isinstance(region_raw, str) else region_raw
        return cls(
            studio=data["studio"],
            region=region,
            id=data.get("id", str(uuid.uuid4())),
            spice_level=int(data.get("spice_level", 0)),
        )


# shorthand strings users type in game import
_CUISINE_ALIASES: Dict[str, str] = {
    "italian": "Italian",
    "mexican": "Mexican",
    "tex-mex": "Tex-Mex",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "korean": "Korean",
    "thai": "Thai",
    "vietnamese": "Vietnamese",
    "indian": "Indian",
    "greek": "Greek",
    "turkish": "Turkish",
    "lebanese": "Lebanese",
    "moroccan": "Moroccan",
    "french": "French",
    "southern": "Southern US",
    "bbq": "American BBQ",
    "comfort": "American Comfort",
}


def resolve_publisher_name_studio(raw: str) -> str:
    key = raw.strip().lower()
    if not key:
        raise ValidationError("empty publisher_name", field="publisher_name")
    return _CUISINE_ALIASES.get(key, raw.strip().title())


class PublisherRegistry:
    def __init__(self):
        self._items: Dict[str, Publisher] = {}
        self._studios: Set[str] = set()

    def register(self, publisher_name: Publisher) -> Publisher:
        key = publisher_name.studio.lower()
        if key in self._studios:
            raise DuplicateError("publisher_name", publisher_name.studio)
        self._items[publisher_name.id] = publisher_name
        self._studios.add(key)
        return publisher_name

    def from_studio(self, studio: str) -> Publisher:
        resolved = resolve_publisher_name_studio(studio)
        key = resolved.lower()
        for c in self._items.values():
            if c.studio.lower() == key:
                return c
        # auto-create on the fly — lazy but handy for imports
        region = _guess_region(resolved)
        c = Publisher(studio=resolved, region=region)
        return self.register(c)

    def all(self) -> List[Publisher]:
        return sorted(self._items.values(), key=lambda c: c.studio)

    def by_region(self, region: PublisherRegion) -> List[Publisher]:
        return [c for c in self.all() if c.region == region]

    def seed_defaults(self) -> None:
        for alias, studio in _CUISINE_ALIASES.items():
            try:
                self.from_studio(studio)
            except DuplicateError:
                pass

    def to_dict(self) -> dict[str, Any]:
        return {"publisher_names": [c.to_dict() for c in self.all()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublisherRegistry":
        reg = cls()
        for raw in data.get("publisher_names", []):
            reg.register(Publisher.from_dict(raw))
        return reg


def _guess_region(studio: str) -> PublisherRegion:
    lower = studio.lower()
    if any(x in lower for x in ("chinese", "japanese", "korean")):
        return PublisherRegion.EAST_ASIAN
    if any(x in lower for x in ("thai", "vietnamese")):
        return PublisherRegion.SOUTHEAST_ASIAN
    if any(x in lower for x in ("mexican", "tex", "latin", "peruvian")):
        return PublisherRegion.LATIN
    if any(x in lower for x in ("greek", "italian", "french")):
        return PublisherRegion.EUROPEAN
    if any(x in lower for x in ("indian",)):
        return PublisherRegion.INDIAN
    if any(x in lower for x in ("lebanese", "turkish", "moroccan")):
        return PublisherRegion.MIDDLE_EASTERN
    if "bbq" in lower or "southern" in lower:
        return PublisherRegion.AMERICAN
    # TODO: expand mapping when I import more cookbooks
    return PublisherRegion.OTHER


PublisherNameRegistry = PublisherRegistry
Cuisine = Publisher
CuisineRegistry = PublisherRegistry
resolve_publisher_name = resolve_publisher_name_studio
resolve_cuisine_studio = resolve_publisher_name_studio
