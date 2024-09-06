"""Append-only audit trail for cookbook mutations.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class AuditLog:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def record(
        self,
        action: str,
        entity: str = "system",
        entity_id: str = "",
        *,
        actor: str = "local",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
        **extra: Any,
    ) -> dict:
        merged = dict(details or {})
        if detail:
            merged["detail"] = detail
        merged.update(extra)
        entry = {
            "id": uuid.uuid4().hex[:16],
            "timestamp": _utc_now(),
            "action": action,
            "entity": entity,
            "entity_id": entity_id or uuid.uuid4().hex[:8],
            "actor": actor,
            "details": merged,
        }
        return self.storage.append_audit(entry)

    def list_entries(
        self,
        *,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        rows = self.storage.list_audit()
        if entity:
            rows = [r for r in rows if r.get("entity") == entity]
        if entity_id:
            rows = [r for r in rows if r.get("entity_id") == entity_id]
        if action:
            rows = [r for r in rows if r.get("action") == action]
        rows.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        if limit:
            rows = rows[:limit]
        return rows

    def since(self, iso_timestamp: str) -> list[dict]:
        return [r for r in self.storage.list_audit() if r.get("timestamp", "") >= iso_timestamp]

    def wrap_mutation(self, action: str, entity: str, entity_id: str, fn):
        """Context helper — log after successful fn()."""
        result = fn()
        self.record(action, entity, entity_id)
        return result

    def export_text(self, limit: int = 50) -> str:
        lines = []
        for row in self.list_entries(limit=limit):
            detail = row.get("details") or {}
            extra = f" {detail}" if detail else ""
            lines.append(
                f"{row.get('timestamp')} [{row.get('action')}] "
                f"{row.get('entity')}:{row.get('entity_id')} by {row.get('actor')}{extra}"
            )
        return "\n".join(lines) if lines else "(empty audit log)"

    def game_history(self, game_id: str) -> list[dict]:
        return self.list_entries(entity="games", entity_id=game_id)

    def count_by_action(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.storage.list_audit():
            action = row.get("action", "unknown")
            counts[action] = counts.get(action, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def prune_old(self, keep: int = 500, *, dry_run: bool = True) -> int:
        rows = self.storage.list_audit()
        if len(rows) <= keep:
            return 0
        to_remove = len(rows) - keep
        if dry_run:
            return to_remove
        # FIXME: storage has no bulk audit delete — mutate directly
        def _trim(data):
            audit = data.get("audit", [])
            audit.sort(key=lambda r: r.get("timestamp", ""))
            data["audit"] = audit[-keep:]

        self.storage.mutate(_trim)
        return to_remove

    # intentionally append-only — no delete/update on individual entries
