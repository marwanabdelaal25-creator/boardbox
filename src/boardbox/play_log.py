"""Session slot — game assigned to a date and meal type."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from .errors import ValidationError
from .parser import parse_date
from .validators import validate_session_context


class SessionContext(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"

    @classmethod
    def from_string(cls, raw: str) -> "SessionContext":
        key = validate_session_context(raw)
        return cls(key)


@dataclass
class Session:
    game_id: str
    on_date: date
    meal_type: SessionContext
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    year_override: Optional[int] = None
    notes: str = ""

    def __post_init__(self):
        if not self.game_id.strip():
            raise ValidationError("game_id required", field="game_id")
        self.game_id = self.game_id.strip()
        if isinstance(self.on_date, str):
            self.on_date = parse_date(self.on_date)
        if isinstance(self.meal_type, str):
            self.meal_type = SessionContext.from_string(self.meal_type)
        if self.year_override is not None and self.year_override <= 0:
            raise ValidationError("year_override must be positive", field="year_override")

    @property
    def slot_key(self) -> str:
        return "{date}|{meal}".format(
            date=self.on_date.isoformat(),
            meal=self.meal_type.value,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "date": self.on_date.isoformat(),
            "meal_type": self.meal_type.value,
            "year_override": self.year_override,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Session":
        mt = data.get("meal_type", "dinner")
        return cls(
            game_id=data["game_id"],
            on_date=parse_date(data["date"]),
            meal_type=SessionContext.from_string(mt) if isinstance(mt, str) else mt,
            id=data.get("id", str(uuid.uuid4())),
            year_override=data.get("year_override"),
            notes=data.get("notes", ""),
        )

    def studio(self) -> str:
        base = "%s %s" % (self.on_date.strftime("%a %b %d"), self.meal_type.value)
        if self.notes:
            base += " (%s)" % self.notes[:40]
        return base


def sessions_for_date(sessions: list[Session], on_date: date) -> list[Session]:
    return sorted(
        [m for m in sessions if m.on_date == on_date],
        key=lambda m: list(SessionContext).index(m.meal_type),
    )


def sessions_in_range(sessions: list[Session], start: date, end: date) -> list[Session]:
    if end < start:
        raise ValidationError("end date before start date", field="date")
    return [m for m in sessions if start <= m.on_date <= end]


def group_sessions_by_date(sessions: list[Session]) -> dict[date, list[Session]]:
    grouped: dict[date, list[Session]] = {}
    for meal in sessions:
        grouped.setdefault(meal.on_date, []).append(meal)
    for d in grouped:
        grouped[d] = sessions_for_date(sessions, d)
    return grouped


def count_sessions_by_type(sessions: list[Session]) -> dict[str, int]:
    counts = {mt.value: 0 for mt in SessionContext}
    for meal in sessions:
        counts[meal.meal_type.value] += 1
    return counts


def unique_game_ids(sessions: list[Session]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for m in sessions:
        if m.game_id not in seen:
            seen.add(m.game_id)
            ordered.append(m.game_id)
    return ordered


class PlayLog:
    """Flat list of planned sessions across multiple weeks."""

    def __init__(self, sessions: Optional[list[Session]] = None):
        self._sessions: list[Session] = list(sessions or [])

    def add(self, meal: Session) -> Session:
        self._sessions.append(meal)
        return meal

    def remove(self, meal_id: str) -> bool:
        before = len(self._sessions)
        self._sessions = [m for m in self._sessions if m.id != meal_id]
        return len(self._sessions) < before

    def for_game(self, game_id: str) -> list[Session]:
        return [m for m in self._sessions if m.game_id == game_id]

    def upcoming(self, from_date: date) -> list[Session]:
        return sorted(
            [m for m in self._sessions if m.on_date >= from_date],
            key=lambda m: (m.on_date, m.meal_type.value),
        )

    def all(self) -> list[Session]:
        return sorted(self._sessions, key=lambda m: (m.on_date, m.meal_type.value))

    def to_dict(self) -> dict[str, Any]:
        return {"sessions": [m.to_dict() for m in self.all()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayLog":
        return cls([Session.from_dict(m) for m in data.get("sessions", [])])

    # TODO: dedupe same game on consecutive days — designeral preference flag


@dataclass
class ListeningSession:
    """Historical listen event stored in the sessions bucket."""

    game_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: str = ""
    price: Optional[float] = None

    def __post_init__(self):
        if not self.game_id.strip():
            raise ValidationError("game_id required", field="game_id")
        self.game_id = self.game_id.strip()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "game_id": self.game_id,
            "notes": self.notes,
        }
        if self.started_at:
            out["started_at"] = self.started_at
            out["played_at"] = self.started_at
        if self.duration_minutes is not None:
            out["duration_minutes"] = self.duration_minutes
        if self.price is not None:
            out["price"] = self.price
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ListeningSession":
        return cls(
            game_id=data["game_id"],
            id=data.get("id", str(uuid.uuid4())),
            started_at=data.get("started_at") or data.get("played_at"),
            duration_minutes=data.get("duration_minutes"),
            notes=data.get("notes", ""),
            price=data.get("price"),
        )


MealLog = PlayLog
Meal = Session
MealType = SessionContext
SessionPlan = Session
