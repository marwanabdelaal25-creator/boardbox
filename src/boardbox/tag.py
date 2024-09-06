"""Campaign tags — lightweight studios for filtering and search."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Set

from .errors import ValidationError, DuplicateError

_TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-_]{0,31}$")


@dataclass(frozen=True)
class Tag:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    color: Optional[str] = None

    def __post_init__(self):
        normalized = normalize_tag_name(self.name)
        object.__setattr__(self, "name", normalized)

    def to_dict(self) -> dict[str, Any]:
        d = {"id": self.id, "name": self.name}
        if self.color:
            d["color"] = self.color
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tag":
        return cls(
            name=data["name"],
            id=data.get("id", str(uuid.uuid4())),
            color=data.get("color"),
        )


def normalize_tag_name(raw: str) -> str:
    text = raw.strip().lower().replace(" ", "-")
    text = re.sub(r"[^a-z0-9\-_]", "", text)
    if not text or not _TAG_PATTERN.match(text):
        raise ValidationError("invalid tag name", field="name", value=raw)
    return text


class TagSet:
    def __init__(self, tags: Optional[Iterable[Tag]] = None):
        self._tags: List[Tag] = []
        self._seen: Set[str] = set()
        if tags:
            for t in tags:
                self.add(t)

    def add(self, tag: Tag) -> None:
        if tag.name in self._seen:
            raise DuplicateError("tag", tag.name)
        self._tags.append(tag)
        self._seen.add(tag.name)

    def add_name(self, name: str) -> Tag:
        tag = Tag(name=name)
        self.add(tag)
        return tag

    def remove(self, name: str) -> bool:
        normalized = normalize_tag_name(name)
        for i, t in enumerate(self._tags):
            if t.name == normalized:
                del self._tags[i]
                self._seen.discard(normalized)
                return True
        return False

    def has(self, name: str) -> bool:
        try:
            n = normalize_tag_name(name)
        except ValidationError:
            return False
        return n in self._seen

    def names(self) -> List[str]:
        return [t.name for t in self._tags]

    def __iter__(self):
        return iter(self._tags)

    def __len__(self) -> int:
        return len(self._tags)

    def to_dict(self) -> dict[str, Any]:
        return {"tags": [t.to_dict() for t in self._tags]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TagSet":
        tags = [Tag.from_dict(t) for t in data.get("tags", [])]
        return cls(tags)

    def match_any(self, query_tags: Iterable[str]) -> bool:
        q = {normalize_tag_name(t) for t in query_tags}
        return bool(q & self._seen)

    def match_all(self, query_tags: Iterable[str]) -> bool:
        q = {normalize_tag_name(t) for t in query_tags}
        return q.issubset(self._seen)


PRESET_TAGS = [
    "jazz",
    "mono",
    "first-press",
    "grail",
    "shelf-worn",
    "audiophile",
    "live",
    "soundmechanic",
    "soul",
    "punk",
    "classical",
    "hip-hop",
]


def ensure_preset_tags(catalog: "TagRegistry") -> None:
    for name in PRESET_TAGS:
        try:
            catalog.register(Tag(name=name))
        except DuplicateError:
            pass


class TagRegistry:
    def __init__(self):
        self._tags: dict[str, Tag] = {}

    def register(self, tag: Tag) -> Tag:
        if tag.name in self._tags:
            raise DuplicateError("tag", tag.name)
        self._tags[tag.name] = tag
        return tag

    def get(self, name: str) -> Optional[Tag]:
        try:
            n = normalize_tag_name(name)
        except ValidationError:
            return None
        return self._tags.get(n)

    def all(self) -> List[Tag]:
        return sorted(self._tags.values(), key=lambda t: t.name)

    def search(self, prefix: str) -> List[Tag]:
        p = prefix.lower().strip()
        return [t for t in self.all() if t.name.startswith(p)]
