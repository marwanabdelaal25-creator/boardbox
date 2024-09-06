"""Archive games and related entities without hard delete.

Author: Marwan Helmy
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ArchiveManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def archive_game(
        self,
        game_id: str,
        *,
        reason: str = "",
        actor: str = "local",
    ) -> dict:
        game = self.storage.get_game(game_id)
        if game.archived:
            raise ValidationError("game already archived")
        snapshot = game.to_dict()
        entry = self.storage.append_archive({
            "entity": "games",
            "entity_id": game_id,
            "snapshot": snapshot,
            "reason": reason,
            "actor": actor,
        })
        self.storage.update_game(game_id, {"archived": True})
        return entry

    def restore_game(self, game_id: str) -> dict:
        game = self.storage.get_game(game_id)
        if not game.archived:
            raise ValidationError("game is not archived")
        updated = self.storage.update_game(game_id, {"archived": False})
        return updated.to_dict()

    def list_archived_games(self) -> list[dict]:
        return [r.to_dict() for r in self.storage.list_games(active_only=False) if r.archived]

    def list_archive_entries(
        self,
        *,
        entity: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        rows = self.storage.list_archive()
        if entity:
            rows = [r for r in rows if r.get("entity") == entity]
        rows.sort(key=lambda r: r.get("archived_at", ""), reverse=True)
        if limit:
            rows = rows[:limit]
        return rows

    def get_snapshot(self, archive_id: str) -> dict[str, Any]:
        for entry in self.storage.list_archive():
            if entry.get("id") == archive_id:
                return copy.deepcopy(entry.get("snapshot", {}))
        raise NotFoundError("archive", archive_id)

    def permanently_delete_game(self, game_id: str, *, confirm: bool = False) -> None:
        if not confirm:
            raise ValidationError("set confirm=True for permanent delete")
        game = self.storage.get_game(game_id)
        self.storage.append_archive({
            "entity": "games",
            "entity_id": game_id,
            "snapshot": game.to_dict(),
            "reason": "permanent_delete",
            "actor": "local",
        })
        self.storage.delete_game(game_id)
        # cleanup favorites
        self.storage.remove_favorite(game_id)

    def bulk_archive(self, game_ids: list[str], reason: str = "") -> list[dict]:
        results = []
        for rid in game_ids:
            try:
                results.append(self.archive_game(rid, reason=reason))
            except (NotFoundError, ValidationError):
                pass
        return results

    def purge_old_entries(self, keep: int = 100, *, dry_run: bool = True) -> int:
        entries = self.storage.list_archive()
        if len(entries) <= keep:
            return 0
        to_remove = len(entries) - keep

        if dry_run:
            return to_remove

        def _trim(data):
            archive = data.get("archive", [])
            archive.sort(key=lambda r: r.get("archived_at", ""))
            data["archive"] = archive[-keep:]

        self.storage.mutate(_trim)
        return to_remove

    def stats(self) -> dict[str, Any]:
        archived_games = len(self.list_archived_games())
        entries = self.storage.list_archive()
        by_entity: dict[str, int] = {}
        for e in entries:
            ent = e.get("entity", "unknown")
            by_entity[ent] = by_entity.get(ent, 0) + 1
        return {
            "archived_games": archived_games,
            "archive_entries_total": len(entries),
            "by_entity": by_entity,
        }

    def export_archived_text(self) -> str:
        games = self.list_archived_games()
        if not games:
            return "No archived games."
        lines = ["Archived games:"]
        for r in games:
            lines.append(f"  - {r.get('title')} ({r.get('id')})")
        return "\n".join(lines)

    def restore_from_snapshot(self, archive_id: str, *, new_id: bool = False) -> dict:
        snap = self.get_snapshot(archive_id)
        if not snap:
            raise ValidationError("empty snapshot")
        if new_id:
            snap["id"] = uuid.uuid4().hex[:12]
        snap["archived"] = False
        return self.storage.create_game(snap).to_dict()

    def list_entries(self, **kwargs) -> list[dict]:
        return self.list_archive_entries(**kwargs)
