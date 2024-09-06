"""Export weekly menu as text or markdown.

Author: Marwan Helmy
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .storage import JsonStorage

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class ExportMenu:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _week_start(self, ref: Optional[datetime] = None) -> datetime:
        ref = ref or datetime.now(timezone.utc)
        start = ref - timedelta(days=ref.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    def _find_plan(self, week_start: datetime) -> Optional[dict]:
        iso = week_start.date().isoformat()
        for plan in self.storage.list_campaigns():
            if plan.get("week_start", "")[:10] == iso:
                return plan
        return None

    def _game_title(self, game_id: str) -> str:
        try:
            return self.storage.get_game(game_id).title
        except Exception:
            return game_id

    def _days_from_plan(self, plan: dict) -> dict[str, list[str]]:
        days: dict[str, list[str]] = {d: [] for d in WEEKDAYS}
        slots = plan.get("days") or plan.get("slots") or {}
        if isinstance(slots, dict):
            for day, entries in slots.items():
                key = day.capitalize() if day.lower() in [d.lower() for d in WEEKDAYS] else day
                if key not in days and day in WEEKDAYS:
                    key = day
                titles = []
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, str):
                            titles.append(self._game_title(entry))
                        elif isinstance(entry, dict):
                            rid = entry.get("game_id", "")
                            meal = entry.get("meal", "dinner")
                            titles.append(f"{self._game_title(rid)} ({meal})")
                if key in days:
                    days[key] = titles
                else:
                    days[key] = titles  # allow custom day keys
        return days

    def build_menu_data(self, ref: Optional[datetime] = None) -> dict[str, Any]:
        week_start = self._week_start(ref)
        plan = self._find_plan(week_start)
        if not plan:
            return {
                "week_start": week_start.date().isoformat(),
                "plan_id": None,
                "days": {d: [] for d in WEEKDAYS},
                "notes": "",
            }
        return {
            "week_start": week_start.date().isoformat(),
            "plan_id": plan.get("id"),
            "days": self._days_from_plan(plan),
            "notes": plan.get("notes", ""),
        }

    def export_text(self, ref: Optional[datetime] = None) -> str:
        data = self.build_menu_data(ref)
        lines = [
            f"Weekly Menu — week of {data['week_start']}",
            "",
        ]
        if not data["plan_id"]:
            lines.append("(no meal plan found for this week)")
            return "\n".join(lines)
        for day in WEEKDAYS:
            sessions = data["days"].get(day, [])
            lines.append(day + ":")
            if sessions:
                for m in sessions:
                    lines.append(f"  - {m}")
            else:
                lines.append("  - (empty)")
            lines.append("")
        if data["notes"]:
            lines.append(f"Notes: {data['notes']}")
        return "\n".join(lines).rstrip()

    def export_markdown(self, ref: Optional[datetime] = None) -> str:
        data = self.build_menu_data(ref)
        lines = [
            f"# Weekly Menu",
            "",
            f"**Week of:** {data['week_start']}",
            "",
        ]
        if not data["plan_id"]:
            lines.append("_No meal plan found for this week._")
            return "\n".join(lines)
        for day in WEEKDAYS:
            sessions = data["days"].get(day, [])
            lines.append(f"## {day}")
            if sessions:
                for m in sessions:
                    lines.append(f"- {m}")
            else:
                lines.append("- _empty_")
            lines.append("")
        if data["notes"]:
            lines.append(f"> {data['notes']}")
        return "\n".join(lines).rstrip()

    def wishlist_from_menu(self, ref: Optional[datetime] = None) -> list[str]:
        data = self.build_menu_data(ref)
        game_ids = []
        plan = self._find_plan(self._week_start(ref))
        if not plan:
            return []
        slots = plan.get("days") or plan.get("slots") or {}
        for entries in slots.values():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, str):
                    game_ids.append(entry)
                elif isinstance(entry, dict) and entry.get("game_id"):
                    game_ids.append(entry["game_id"])
        lines = []
        seen: set[str] = set()
        for rid in game_ids:
            try:
                game = self.storage.get_game(rid)
            except Exception:
                continue
            for ing in game.mechanics:
                key = ing.name.lower()
                if key not in seen:
                    seen.add(key)
                    unit = f" {ing.unit}" if ing.unit else ""
                    lines.append(f"- {ing.quantity}{unit} {ing.name}".strip())
        lines.sort()
        return lines

    def export_wishlist_markdown(self, ref: Optional[datetime] = None) -> str:
        items = self.wishlist_from_menu(ref)
        week = self._week_start(ref).date().isoformat()
        lines = [f"# Shopping List — week of {week}", ""]
        if not items:
            lines.append("_No games in meal plan._")
        else:
            lines.extend(items)
        return "\n".join(lines)


def list_options() -> list[str]:
    return ["Export %s" % studio for studio in [
        "JSON snapshot",
        "CSV games",
        "JSONL full dump",
        "weekly menu markdown",
        "shopping list markdown",
    ]]


MenuExporter = ExportMenu
