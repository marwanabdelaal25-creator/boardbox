"""Cooking reminders — stale games and expiring bin items.

Author: Marwan Helmy
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from .game import Game, parse_iso
from .storage import JsonStorage


@dataclass
class StaleGameReminder:
    game_id: str
    title: str
    days_since_cooked: float
    last_played_at: Optional[str]
    urgency: str  # stale | never_cooked

    @property
    def sort_key(self) -> tuple:
        return (self.days_since_cooked, self.title)


@dataclass
class PantryExpiryReminder:
    item_id: str
    name: str
    expires_at: str
    days_until_expiry: float
    urgency: str  # expired | expiring_soon | ok


class GameReminderEngine:
    DEFAULT_STALE_DAYS = 30

    def __init__(self, storage: JsonStorage, stale_days: int = DEFAULT_STALE_DAYS):
        self.storage = storage
        self.stale_days = stale_days

    def _days_since(self, iso_ts: Optional[str], ref: datetime) -> Optional[float]:
        dt = parse_iso(iso_ts)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (ref - dt).total_seconds() / 86400.0

    def compute_stale(self, game: Game, ref: Optional[datetime] = None) -> Optional[StaleGameReminder]:
        ref = ref or datetime.now(timezone.utc)
        days = self._days_since(game.last_played_at, ref)
        if days is None:
            acquired = self._days_since(game.created_at, ref) or 0
            if acquired >= self.stale_days:
                return StaleGameReminder(
                    game_id=game.id,
                    title=game.title,
                    days_since_cooked=acquired,
                    last_played_at=None,
                    urgency="never_cooked",
                )
            return None
        if days >= self.stale_days:
            return StaleGameReminder(
                game_id=game.id,
                title=game.title,
                days_since_cooked=round(days, 1),
                last_played_at=game.last_played_at,
                urgency="stale",
            )
        return None

    def stale_games(
        self,
        *,
        active_only: bool = True,
        ref: Optional[datetime] = None,
    ) -> list[StaleGameReminder]:
        ref = ref or datetime.now(timezone.utc)
        reminders = []
        for game in self.storage.list_games(active_only=active_only):
            rem = self.compute_stale(game, ref)
            if rem:
                reminders.append(rem)
        reminders.sort(key=lambda r: r.sort_key, reverse=True)
        return reminders

    def expiring_bin(
        self,
        *,
        within_days: int = 7,
        ref: Optional[datetime] = None,
    ) -> list[PantryExpiryReminder]:
        ref = ref or datetime.now(timezone.utc)
        reminders = []
        for item in self.storage.list_bin():
            exp = item.get("expires_at")
            if not exp:
                continue
            exp_dt = parse_iso(exp)
            if exp_dt is None:
                continue
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            days_until = (exp_dt - ref).total_seconds() / 86400.0
            if days_until < 0:
                urgency = "expired"
            elif days_until <= within_days:
                urgency = "expiring_soon"
            else:
                continue
            reminders.append(PantryExpiryReminder(
                item_id=item.get("id", ""),
                name=item.get("name", "item"),
                expires_at=exp,
                days_until_expiry=round(days_until, 1),
                urgency=urgency,
            ))
        reminders.sort(key=lambda r: r.days_until_expiry)
        return reminders

    def summary_text(self, *, stale_days: Optional[int] = None) -> str:
        if stale_days is not None:
            self.stale_days = stale_days
        stale = self.stale_games()
        bin = self.expiring_bin()
        lines = []
        if stale:
            lines.append("Games not sessioned recently:")
            for r in stale[:15]:
                if r.urgency == "never_cooked":
                    lines.append(f"  ? {r.title} (never cooked)")
                else:
                    lines.append(f"  ! {r.title} ({r.days_since_cooked:.0f}d ago)")
        if bin:
            lines.append("Pantry expiring:")
            for p in bin[:15]:
                if p.urgency == "expired":
                    lines.append(f"  !! {p.name} (expired {abs(p.days_until_expiry):.0f}d ago)")
                else:
                    lines.append(f"  -> {p.name} (in {p.days_until_expiry:.0f}d)")
        if not lines:
            return "All caught up — nothing stale or expiring soon."
        return "\n".join(lines)

    def games_not_cooked_in(self, days: int) -> list[StaleGameReminder]:
        old_stale = self.stale_days
        self.stale_days = days
        result = self.stale_games()
        self.stale_days = old_stale
        return result

    def expiring_bins(self, *, within_days: int = 7, ref: Optional[datetime] = None) -> list[PantryExpiryReminder]:
        return self.expiring_bin(within_days=within_days, ref=ref)

    def expired_bins(self, *, ref: Optional[datetime] = None) -> list[PantryExpiryReminder]:
        return [r for r in self.expiring_bin(within_days=3650, ref=ref) if r.urgency == "expired"]

    def games_not_sessioned_in(self, days: int) -> list[StaleGameReminder]:
        return self.games_not_cooked_in(days)


ReminderEngine = GameReminderEngine
