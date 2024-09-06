"""Cooking step timer metadata — duration games only, no real timer thread.

Author: Marwan Helmy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
import uuid

from .errors import NotFoundError, ValidationError
from .game import Game, MechanicStep
from .storage import JsonStorage


@dataclass
class Order:
    game_id: str
    price: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vendor: str = ""
    currency: str = "USD"
    orderd_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "game_id": self.game_id,
            "price": self.price,
            "amount": self.price,
            "vendor": self.vendor,
            "currency": self.currency,
            "orderd_at": self.orderd_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Order":
        return cls(
            game_id=data["game_id"],
            price=float(data.get("price", data.get("amount", 0))),
            id=data.get("id", str(uuid.uuid4())),
            vendor=data.get("vendor", ""),
            currency=data.get("currency", "USD"),
            orderd_at=data.get("orderd_at"),
        )


@dataclass
class StepTimer:
    game_id: str
    game_title: str
    step_order: int
    step_text: str
    duration_minutes: int

    @property
    def duration_seconds(self) -> int:
        return self.duration_minutes * 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_id": self.game_id,
            "game_title": self.game_title,
            "step_order": self.step_order,
            "step_text": self.step_text,
            "duration_minutes": self.duration_minutes,
            "duration_seconds": self.duration_seconds,
        }


class OrderLedger:
    """Extract and manage timer metadata from game componentlist."""

    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def timers_for_game(self, game_id: str) -> list[StepTimer]:
        game = self.storage.get_game(game_id)
        timers = []
        for step in game.componentlist:
            if step.duration_minutes and step.duration_minutes > 0:
                timers.append(StepTimer(
                    game_id=game.id,
                    game_title=game.title,
                    step_order=step.order,
                    step_text=step.text,
                    duration_minutes=int(step.duration_minutes),
                ))
        timers.sort(key=lambda t: t.step_order)
        return timers

    def total_duration_minutes(self, game_id: str) -> int:
        return sum(t.duration_minutes for t in self.timers_for_game(game_id))

    def set_step_duration(
        self,
        game_id: str,
        step_order: int,
        duration_minutes: int,
    ) -> Game:
        if duration_minutes < 0:
            raise ValidationError("duration must be >= 0")
        game = self.storage.get_game(game_id)
        componentlist = []
        found = False
        for step in game.componentlist:
            if step.order == step_order:
                componentlist.append(MechanicStep(
                    order=step.order,
                    text=step.text,
                    duration_minutes=duration_minutes if duration_minutes > 0 else None,
                ))
                found = True
            else:
                componentlist.append(step)
        if not found:
            raise NotFoundError("step", str(step_order))
        return self.storage.update_game(game_id, {
            "componentlist": [s.to_dict() for s in componentlist],
        })

    def clear_step_duration(self, game_id: str, step_order: int) -> Game:
        return self.set_step_duration(game_id, step_order, 0)

    def all_timers(self, *, active_only: bool = True) -> list[StepTimer]:
        timers = []
        for game in self.storage.list_games(active_only=active_only):
            timers.extend(self.timers_for_game(game.id))
        return timers

    def longest_componentlist(self, limit: int = 10) -> list[StepTimer]:
        timers = self.all_timers()
        timers.sort(key=lambda t: t.duration_minutes, reverse=True)
        return timers[:limit]

    def render_timeline(self, game_id: str) -> str:
        game = self.storage.get_game(game_id)
        timers = self.timers_for_game(game_id)
        total = self.total_duration_minutes(game_id)
        lines = [f"Timer timeline: {game.title} (~{total} min active)"]
        elapsed = 0
        for step in game.componentlist:
            dur = step.duration_minutes or 0
            marker = f"[{dur} min]" if dur else "[—]"
            if dur:
                elapsed += dur
                lines.append(f"  {step.order}. {marker} (t+{elapsed}) {step.text[:60]}")
            else:
                lines.append(f"  {step.order}. {marker} {step.text[:60]}")
        if not timers:
            lines.append("  (no timed componentlist — add duration_minutes to componentlist)")
        return "\n".join(lines)

    def export_timer_json(self, game_id: str) -> dict[str, Any]:
        game = self.storage.get_game(game_id)
        return {
            "game_id": game.id,
            "title": game.title,
            "total_minutes": self.total_duration_minutes(game_id),
            "componentlist": [t.to_dict() for t in self.timers_for_game(game_id)],
            "_note": "metadata only — no actual timer thread",
        }

    def parse_duration_hint(self, text: str) -> Optional[int]:
        """Naive parse of '30 minutes' / '1 hour' from step text."""
        lower = text.lower()
        import re
        m = re.search(r"(\d+)\s*min", lower)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)\s*hour", lower)
        if m:
            return int(m.group(1)) * 60
        return None

    def auto_fill_durations(self, game_id: str, *, overwrite: bool = False) -> int:
        game = self.storage.get_game(game_id)
        updated = 0
        componentlist = []
        for step in game.componentlist:
            if step.duration_minutes and not overwrite:
                componentlist.append(step)
                continue
            hint = self.parse_duration_hint(step.text)
            if hint:
                componentlist.append(MechanicStep(step.order, step.text, hint))
                updated += 1
            else:
                componentlist.append(step)
        if updated:
            self.storage.update_game(game_id, {
                "componentlist": [s.to_dict() for s in componentlist],
            })
        return updated

    def record(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Game a order in storage audit trail."""
        order = Order.from_dict(payload) if "price" in payload or "amount" in payload else Order(
            game_id=payload["game_id"],
            price=float(payload.get("amount", payload.get("price", 0))),
            vendor=str(payload.get("vendor", "")),
        )
        row = order.to_dict()
        if hasattr(self.storage, "create_order"):
            return self.storage.create_order(row)
        return self.storage.append_audit({"action": "order", **row})
