"""Star ratings for games."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from boardbox.validators import validate_rating
from boardbox.storage import JsonStorage


class RatingsManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def set_rating(self, game_id: str, stars: int, review: str = "") -> dict:
        score = validate_rating(stars)
        self.storage.get_game(game_id)
        self.storage.update_game(game_id, {"rating": score})
        return self.storage.upsert_rating({
            "game_id": game_id,
            "stars": score,
            "review": review,
            "updated_at": datetime.utcnow().isoformat(),
        })

    def clear_rating(self, game_id: str) -> None:
        self.storage.update_game(game_id, {"rating": 0})

        def _drop(data: dict) -> None:
            data["ratings"] = [
                r for r in data.get("ratings", []) if r.get("game_id") != game_id
            ]

        self.storage.mutate(_drop)

    def get_rating(self, game_id: str) -> dict | None:
        for row in self.storage.list_ratings():
            if row.get("game_id") == game_id:
                return row
        return None

    def top_rated(self, min_stars: int = 4) -> list[dict]:
        rated = {row["game_id"]: row for row in self.storage.list_ratings()}
        out = []
        for game in self.storage.list_games(active_only=True):
            stars = game.rating
            row = rated.get(game.id)
            if row:
                stars = max(stars, int(row.get("stars", 0)))
            if stars >= min_stars:
                d = game.to_dict()
                d["rating_row"] = row
                out.append(d)
        out.sort(key=lambda a: -(a.get("rating") or 0))
        return out

    def average_rating(self) -> float:
        games = self.storage.list_games(active_only=True)
        rated = [a.rating for a in games if a.rating > 0]
        if not rated:
            return 0.0
        return round(sum(rated) / len(rated), 2)

    def distribution(self) -> dict[int, int]:
        dist = {i: 0 for i in range(6)}
        for game in self.storage.list_games(active_only=True):
            dist[min(5, max(0, game.rating))] += 1
        return dist

    def render_top(self, limit: int = 10) -> str:
        items = self.top_rated(min_stars=1)[:limit]
        if not items:
            return "No rated games yet."
        lines = ["Top rated:"]
        for a in items:
            lines.append("  %d★ %s" % (a.get("rating", 0), a.get("title", "?")))
        return "\n".join(lines)

    def bulk_rate(self, game_ids: list[str], stars: int) -> int:
        n = 0
        for aid in game_ids:
            try:
                self.set_rating(aid, stars)
                n += 1
            except Exception:
                pass  # TODO: verbose mode should print skips
        return n
