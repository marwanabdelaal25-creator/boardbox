"""Favorite games management.

Author: Marwan Helmy
"""

from __future__ import annotations

from typing import Optional

from .errors import NotFoundError, ValidationError
from .game import Game
from .storage import JsonStorage


class FavoritesManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def list_ids(self) -> list[str]:
        return self.storage.list_favorites()

    def list_games(self, active_only: bool = True) -> list[Game]:
        fav_ids = set(self.list_ids())
        games = []
        for game in self.storage.list_games(active_only=active_only):
            if game.id in fav_ids or game.favorite:
                games.append(game)
        # dedupe by id
        seen = set()
        unique = []
        for r in games:
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)
        unique.sort(key=lambda r: r.title.lower())
        return unique

    def is_favorite(self, game_id: str) -> bool:
        if game_id in self.list_ids():
            return True
        try:
            return self.storage.get_game(game_id).favorite
        except NotFoundError:
            return False

    def add(self, game_id: str) -> list[str]:
        self.storage.get_game(game_id)  # ensure exists
        self.storage.update_game(game_id, {"favorite": True})
        return self.storage.add_favorite(game_id)

    def remove(self, game_id: str) -> list[str]:
        try:
            self.storage.update_game(game_id, {"favorite": False})
        except NotFoundError:
            pass
        return self.storage.remove_favorite(game_id)

    def toggle(self, game_id: str) -> bool:
        if self.is_favorite(game_id):
            self.remove(game_id)
            return False
        self.add(game_id)
        return True

    def sync_flags(self) -> int:
        """Align favorites list with per-game favorite flags — returns fix count."""
        fav_ids = set(self.list_ids())
        changed = 0
        for game in self.storage.list_games(active_only=False):
            in_list = game.id in fav_ids
            flagged = game.favorite
            if flagged and not in_list:
                self.storage.add_favorite(game.id)
                changed += 1
            elif in_list and not flagged:
                self.storage.update_game(game.id, {"favorite": True})
                changed += 1
            elif not flagged and in_list:
                self.storage.remove_favorite(game.id)
                changed += 1
        return changed

    def prune_stale(self) -> list[str]:
        """Remove favorite ids pointing to deleted games."""
        removed = []
        for fid in list(self.list_ids()):
            try:
                self.storage.get_game(fid)
            except NotFoundError:
                self.storage.remove_favorite(fid)
                removed.append(fid)
        return removed

    def top_by_publisher_name(self, publisher_name: Optional[str] = None) -> list[Game]:
        games = self.list_games()
        if publisher_name:
            c = publisher_name.lower()
            games = [r for r in games if r.publisher_name.lower() == c]
        return games

    def count(self) -> int:
        return len(self.list_games(active_only=True))

    def render_list(self) -> str:
        games = self.list_games()
        if not games:
            return "No favorites yet."
        lines = ["Favorites:"]
        for r in games:
            meta = []
            if r.publisher_name:
                meta.append(r.publisher_name)
            if r.format:
                meta.append(r.format)
            suffix = f" ({', '.join(meta)})" if meta else ""
            lines.append(f"  ★ {r.title}{suffix}")
        return "\n".join(lines)

    def bulk_add(self, game_ids: list[str]) -> int:
        added = 0
        for rid in game_ids:
            try:
                if not self.is_favorite(rid):
                    self.add(rid)
                    added += 1
            except NotFoundError:
                pass
        return added

    def export_ids(self) -> list[str]:
        return [r.id for r in self.list_games(active_only=False)]
