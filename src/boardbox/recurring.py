"""Recurring cooking task definitions.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .errors import NotFoundError, ValidationError
from .game import parse_iso
from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RecurringTasks:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def define(
        self,
        title: str,
        interval_days: int,
        *,
        game_id: Optional[str] = None,
        action: str = "cook",
        enabled: bool = True,
    ) -> dict:
        if interval_days < 1:
            raise ValidationError("interval_days must be >= 1")
        if game_id:
            self.storage.get_game(game_id)
        task = {
            "id": uuid.uuid4().hex[:12],
            "title": title,
            "action": action,
            "interval_days": interval_days,
            "game_id": game_id,
            "enabled": enabled,
            "last_run_at": None,
            "created_at": _utc_now(),
        }
        return self.storage.create_recurring(task)

    def list_enabled(self) -> list[dict]:
        return [t for t in self.storage.list_recurring() if t.get("enabled", True)]

    def list_all(self) -> list[dict]:
        return self.storage.list_recurring()

    def disable(self, task_id: str) -> dict:
        return self.storage.update_recurring(task_id, {"enabled": False})

    def enable(self, task_id: str) -> dict:
        return self.storage.update_recurring(task_id, {"enabled": True})

    def mark_done(self, task_id: str) -> dict:
        task = self.storage.update_recurring(task_id, {"last_run_at": _utc_now()})
        rid = task.get("game_id")
        if rid and task.get("action") == "cook":
            try:
                self.storage.create_session({"game_id": rid, "notes": f"recurring:{task_id}"})
            except NotFoundError:
                pass
        return task

    def due_tasks(self, ref: Optional[datetime] = None) -> list[dict]:
        ref = ref or datetime.now(timezone.utc)
        due = []
        for task in self.list_enabled():
            last = parse_iso(task.get("last_run_at"))
            interval = timedelta(days=int(task.get("interval_days", 7)))
            if last is None:
                due.append({**task, "reason": "never_run"})
                continue
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if ref - last >= interval:
                overdue_days = (ref - (last + interval)).days
                due.append({**task, "overdue_days": max(0, overdue_days)})
        due.sort(key=lambda t: t.get("overdue_days", 0), reverse=True)
        return due

    def delete(self, task_id: str) -> None:
        self.storage.delete_recurring(task_id)

    def update(self, task_id: str, patch: dict) -> dict:
        return self.storage.update_recurring(task_id, patch)

    def for_game(self, game_id: str) -> list[dict]:
        return [t for t in self.storage.list_recurring() if t.get("game_id") == game_id]

    def render_due(self) -> str:
        due = self.due_tasks()
        if not due:
            return "No recurring sessions due."
        lines = ["Recurring sessions due:"]
        for t in due:
            overdue = t.get("overdue_days", 0)
            suffix = f" ({overdue}d overdue)" if overdue else ""
            lines.append(f"  - {t.get('title')}{suffix}")
        return "\n".join(lines)

    def next_run_at(self, task_id: str) -> Optional[str]:
        for task in self.storage.list_recurring():
            if task.get("id") != task_id:
                continue
            last = parse_iso(task.get("last_run_at"))
            interval = int(task.get("interval_days", 7))
            if last is None:
                return _utc_now()
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            nxt = last + timedelta(days=interval)
            return nxt.isoformat()
        raise NotFoundError("recurring", task_id)


RecurringSessions = RecurringTasks
RecurringMeals = RecurringTasks
