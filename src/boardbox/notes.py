"""Free-form notes attached to games, sessions, or mechanics."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

from .errors import ValidationError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Note:
    body: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: Optional[datetime] = None
    pinned: bool = False

    def __post_init__(self):
        if not self.body or not self.body.strip():
            raise ValidationError("note body cannot be empty", field="body")
        self.body = self.body.strip()

    def edit(self, new_body: str) -> None:
        if not new_body.strip():
            raise ValidationError("note body cannot be empty", field="body")
        self.body = new_body.strip()
        self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "body": self.body,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "pinned": self.pinned,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Note":
        created = datetime.fromisoformat(data["created_at"])
        updated_raw = data.get("updated_at")
        updated = datetime.fromisoformat(updated_raw) if updated_raw else None
        return cls(
            body=data["body"],
            id=data.get("id", str(uuid.uuid4())),
            created_at=created,
            updated_at=updated,
            pinned=data.get("pinned", False),
        )

    def preview(self, max_len: int = 80) -> str:
        text = self.body.replace("\n", " ")
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."


@dataclass
class NoteCampaign:
    """Multiple notes on one entity — pinned float to top."""

    notes: List[Note] = field(default_factory=list)

    def add(self, body: str, *, pinned: bool = False) -> Note:
        note = Note(body=body, pinned=pinned)
        self.notes.append(note)
        self._sort()
        return note

    def remove(self, note_id: str) -> bool:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n.id != note_id]
        return len(self.notes) < before

    def get(self, note_id: str) -> Optional[Note]:
        for n in self.notes:
            if n.id == note_id:
                return n
        return None

    def _sort(self) -> None:
        self.notes.sort(key=lambda n: (not n.pinned, n.created_at))

    def latest(self) -> Optional[Note]:
        if not self.notes:
            return None
        return max(self.notes, key=lambda n: n.updated_at or n.created_at)

    def to_dict(self) -> dict[str, Any]:
        return {"notes": [n.to_dict() for n in self.notes]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NoteCampaign":
        notes = [Note.from_dict(n) for n in data.get("notes", [])]
        coll = cls(notes=notes)
        coll._sort()
        return coll

    def merge_text(self, separator: str = "\n---\n") -> str:
        if not self.notes:
            return ""
        parts = []
        for n in self.notes:
            header = "[pinned] " if n.pinned else ""
            parts.append("{0}{1}".format(header, n.body))
        return separator.join(parts)

    def __len__(self) -> int:
        return len(self.notes)


def truncate_note_body(body: str, limit: int = 500) -> str:
    text = body.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


# HACK: markdown rendering belongs in CLI layer, not domain
def note_to_plaintext(note: Note) -> str:
    return note.body.replace("**", "").replace("*", "")
