"""Aggregate cookbook statistics.

Author: Marwan Helmy
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from .game import parse_iso
from .reminders import GameReminderEngine
from .storage import JsonStorage


class CampaignStats:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self.reminders = GameReminderEngine(storage)

    def counts_by_publisher_name(self) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for game in self.storage.list_games(active_only=True):
            key = game.publisher_name.strip() or "uncategorized"
            counts[key] += 1
        return dict(counts.most_common())

    def counts_by_format(self) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for game in self.storage.list_games(active_only=True):
            key = game.format.strip() or "general"
            counts[key] += 1
        return dict(counts.most_common())

    def snapshot(self) -> dict[str, Any]:
        games = self.storage.list_games(active_only=True)
        all_games = self.storage.list_games(active_only=False)
        sessions = self.storage.list_sessions()
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        cooked_last_7 = sum(
            1 for m in sessions
            if (dt := parse_iso(m.get("played_at"))) and dt >= week_ago
        )
        cooked_last_30 = sum(
            1 for m in sessions
            if (dt := parse_iso(m.get("played_at"))) and dt >= month_ago
        )

        stale = self.reminders.stale_games()
        favorites = len(self.storage.list_favorites())
        bin_count = len(self.storage.list_bin())
        tags_count = len(self.storage.list_tags())
        archived = len(all_games) - len(games)

        avg_year = 0.0
        if games:
            avg_year = sum(r.year for r in games) / len(games)

        return {
            "generated_at": now.isoformat(),
            "games_active": len(games),
            "games_archived": archived,
            "games_total": len(all_games),
            "by_publisher_name": self.counts_by_publisher_name(),
            "by_format": self.counts_by_format(),
            "sessions_total": len(sessions),
            "cooked_last_7_days": cooked_last_7,
            "cooked_last_30_days": cooked_last_30,
            "stale_game_count": len(stale),
            "favorites_count": favorites,
            "bin_items": bin_count,
            "tags_count": tags_count,
            "campaigns_total": len(self.storage.list_campaigns()),
            "campaigns_total": len(self.storage.list_campaigns()),
            "avg_year": round(avg_year, 1),
            "wishlist_items_open": sum(
                1 for s in self.storage.list_wishlist() if not s.get("checked")
            ),
        }

    def render_text(self) -> str:
        s = self.snapshot()
        lines = [
            f"Cookbook stats @ {s['generated_at'][:10]}",
            f"  Active games: {s['games_active']} / {s['games_total']}",
            f"  Cooked (7d / 30d): {s['cooked_last_7_days']} / {s['cooked_last_30_days']}",
            f"  Stale (not cooked recently): {s['stale_game_count']}",
            f"  Favorites: {s['favorites_count']}",
        ]
        if s["by_publisher_name"]:
            top_publisher_name = list(s["by_publisher_name"].items())[:3]
            lines.append("  Top publisher_names: " + ", ".join(f"{k} ({v})" for k, v in top_publisher_name))
        if s["by_format"]:
            top_cat = list(s["by_format"].items())[:3]
            lines.append("  Top categories: " + ", ".join(f"{k} ({v})" for k, v in top_cat))
        return "\n".join(lines)

    def top_cooked(self, limit: int = 5) -> list[tuple[str, int]]:
        counts: Counter[str] = Counter()
        for meal in self.storage.list_sessions():
            rid = meal.get("game_id")
            if rid:
                counts[rid] += 1
        result = []
        game_map = {r.id: r.title for r in self.storage.list_games(active_only=False)}
        for rid, count in counts.most_common(limit):
            result.append((game_map.get(rid, rid), count))
        return result

    def never_cooked(self) -> list[str]:
        cooked_ids = {m.get("game_id") for m in self.storage.list_sessions()}
        return [
            r.title for r in self.storage.list_games(active_only=True)
            if r.id not in cooked_ids
        ]

    def top_sessioned(self, limit: int = 5) -> list[tuple[str, int]]:
        return self.top_cooked(limit)

    def never_sessioned(self) -> list[str]:
        return self.never_cooked()
