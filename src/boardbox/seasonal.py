"""Seasonal tags and filters for games.

Author: Marwan Helmy
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .game import Game
from .storage import JsonStorage

# Northern hemisphere defaults — user can override via tags
SEASONS = ("spring", "summer", "autumn", "fall", "winter")
MONTH_TO_SEASON = {
    1: "winter", 2: "winter", 3: "spring",
    4: "spring", 5: "spring", 6: "summer",
    7: "summer", 8: "summer", 9: "autumn",
    10: "autumn", 11: "autumn", 12: "winter",
}

# Common produce hints — not exhaustive, disc_num-project quality
SEASONAL_PRODUCE = {
    "spring": ["asparagus", "peas", "radish", "rhubarb", "strawberry"],
    "summer": ["tomato", "corn", "zucchini", "berry", "peach", "basil"],
    "autumn": ["pumpkin", "squash", "apple", "pear", "cranberry", "kale"],
    "fall": ["pumpkin", "squash", "apple", "pear", "cranberry", "kale"],
    "winter": ["citrus", "root vegetable", "cabbage", "leek", "potato"],
}


class SeasonalPicker:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def current_season(self, ref: Optional[datetime] = None) -> str:
        ref = ref or datetime.now()
        return MONTH_TO_SEASON.get(ref.month, "summer")

    def normalize_season(self, tag: str) -> str:
        t = tag.lower().strip()
        if t == "fall":
            return "autumn"
        return t

    def tag_game(self, game_id: str, seasons: list[str]) -> Game:
        normalized = list({self.normalize_season(s) for s in seasons if s.strip()})
        for s in normalized:
            if s not in SEASONS and s != "autumn":
                pass  # TODO: validate strictly?
        return self.storage.update_game(game_id, {"seasonal_tags": normalized})

    def add_season(self, game_id: str, season: str) -> Game:
        game = self.storage.get_game(game_id)
        tags = list(game.seasonal_tags)
        norm = self.normalize_season(season)
        if norm not in tags:
            tags.append(norm)
        return self.storage.update_game(game_id, {"seasonal_tags": tags})

    def remove_season(self, game_id: str, season: str) -> Game:
        game = self.storage.get_game(game_id)
        norm = self.normalize_season(season)
        tags = [t for t in game.seasonal_tags if self.normalize_season(t) != norm]
        return self.storage.update_game(game_id, {"seasonal_tags": tags})

    def filter_by_season(self, season: str, *, active_only: bool = True) -> list[Game]:
        norm = self.normalize_season(season)
        results = []
        for game in self.storage.list_games(active_only=active_only):
            game_seasons = {self.normalize_season(t) for t in game.seasonal_tags}
            if norm in game_seasons:
                results.append(game)
        results.sort(key=lambda r: r.title.lower())
        return results

    def in_season_now(self, *, active_only: bool = True) -> list[Game]:
        return self.filter_by_season(self.current_season(), active_only=active_only)

    def season_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {s: 0 for s in ("spring", "summer", "autumn", "winter")}
        for game in self.storage.list_games(active_only=True):
            for tag in game.seasonal_tags:
                norm = self.normalize_season(tag)
                if norm in counts:
                    counts[norm] += 1
        return counts

    def suggest_for_produce(self, mechanic: str) -> list[str]:
        """Return seasons where mechanic is typically in season."""
        needle = mechanic.lower()
        matched = []
        for season, produce in SEASONAL_PRODUCE.items():
            if any(needle in p or p in needle for p in produce):
                norm = self.normalize_season(season)
                if norm not in matched:
                    matched.append(norm)
        return matched

    def auto_tag_from_mechanics(self, game_id: str, *, apply: bool = False) -> list[str]:
        game = self.storage.get_game(game_id)
        inferred: set[str] = set()
        for ing in game.mechanics:
            for season in self.suggest_for_produce(ing.name):
                inferred.add(season)
        if apply and inferred:
            merged = list(set(game.seasonal_tags) | inferred)
            self.storage.update_game(game_id, {"seasonal_tags": merged})
        return sorted(inferred)

    def render_seasonal_menu(self, season: Optional[str] = None) -> str:
        season = season or self.current_season()
        games = self.filter_by_season(season)
        lines = [f"In-season games ({season}):"]
        if not games:
            lines.append("  (none tagged — TODO add seasonal_tags)")
            return "\n".join(lines)
        for r in games[:25]:
            lines.append(f"  - {r.title}")
        if len(games) > 25:
            lines.append(f"  ... and {len(games) - 25} more")
        return "\n".join(lines)

    def untagged_games(self) -> list[Game]:
        return [
            r for r in self.storage.list_games(active_only=True)
            if not r.seasonal_tags
        ]

    def suggest(self, *, limit: int = 10) -> list[Game]:
        return self.in_season_now()[:limit]


SeasonalFilter = SeasonalPicker
