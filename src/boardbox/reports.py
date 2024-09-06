"""Weekly cooking summary reports.

Author: Marwan Helmy
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .game import parse_iso
from .storage import JsonStorage


class WeeklySessionReport:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _week_bounds(self, ref: Optional[datetime] = None) -> tuple[datetime, datetime]:
        ref = ref or datetime.now(timezone.utc)
        start = ref - timedelta(days=ref.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return start, end

    def _in_range(self, ts: Optional[str], start: datetime, end: datetime) -> bool:
        dt = parse_iso(ts)
        if dt is None:
            return False
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return start <= dt <= end

    def generate(self, ref: Optional[datetime] = None) -> dict[str, Any]:
        start, end = self._week_bounds(ref)
        sessions = [
            m for m in self.storage.list_sessions()
            if self._in_range(m.get("played_at"), start, end)
        ]
        game_map = {r.id: r for r in self.storage.list_games(active_only=False)}

        by_game = Counter(m.get("game_id") for m in sessions)
        by_publisher_name: dict[str, int] = defaultdict(int)
        by_format: dict[str, int] = defaultdict(int)
        unique_games = set()

        for meal in sessions:
            rid = meal.get("game_id")
            if not rid:
                continue
            unique_games.add(rid)
            game = game_map.get(rid)
            if game:
                publisher_name = game.publisher_name or "unknown"
                format = game.format or "general"
                by_publisher_name[publisher_name] += 1
                by_format[format] += 1

        top_games = []
        for rid, count in by_game.most_common(5):
            title = game_map[rid].title if rid in game_map else rid
            top_games.append({"game_id": rid, "title": title, "times": count})

        plans = [
            p for p in self.storage.list_campaigns()
            if p.get("week_start", "")[:10] <= end.date().isoformat()
            and p.get("week_start", "")[:10] >= start.date().isoformat()
        ]

        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "totals": {
                "sessions_logged": len(sessions),
                "unique_games": len(unique_games),
                "campaigns_active": len(plans),
            },
            "top_games": top_games,
            "by_publisher_name": dict(by_publisher_name),
            "by_format": dict(by_format),
            "sessions": sessions,
        }

    def render_text(self, ref: Optional[datetime] = None) -> str:
        report = self.generate(ref)
        t = report["totals"]
        lines = [
            f"Weekly cooking report ({report['period_start'][:10]} – {report['period_end'][:10]})",
            f"  Sessions logged: {t['sessions_logged']} ({t['unique_games']} unique games)",
            f"  Session plans: {t['campaigns_active']}",
        ]
        if report["top_games"]:
            lines.append("  Most cooked:")
            for row in report["top_games"]:
                lines.append(f"    - {row['title']}: {row['times']}x")
        if report["by_publisher_name"]:
            lines.append("  By publisher_name:")
            for k, v in sorted(report["by_publisher_name"].items(), key=lambda kv: -kv[1]):
                lines.append(f"    - {k}: {v}")
        return "\n".join(lines)

    def render_markdown(self, ref: Optional[datetime] = None) -> str:
        report = self.generate(ref)
        t = report["totals"]
        lines = [
            "# Weekly Cooking Report",
            "",
            f"**Period:** {report['period_start'][:10]} to {report['period_end'][:10]}",
            "",
            "## Summary",
            f"- Sessions logged: **{t['sessions_logged']}**",
            f"- Unique games: **{t['unique_games']}**",
            "",
        ]
        if report["top_games"]:
            lines.append("## Most Cooked")
            for row in report["top_games"]:
                lines.append(f"- {row['title']} ({row['times']}x)")
            lines.append("")
        if report["by_format"]:
            lines.append("## By Category")
            for k, v in sorted(report["by_format"].items(), key=lambda kv: -kv[1]):
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def compare_previous_week(self, ref: Optional[datetime] = None) -> dict[str, Any]:
        ref = ref or datetime.now(timezone.utc)
        current = self.generate(ref)
        prev_ref = ref - timedelta(days=7)
        previous = self.generate(prev_ref)
        cur_total = current["totals"]["sessions_logged"]
        prev_total = previous["totals"]["sessions_logged"]
        delta = cur_total - prev_total
        return {
            "current_week": cur_total,
            "previous_week": prev_total,
            "delta": delta,
            "trend": "up" if delta > 0 else ("down" if delta < 0 else "flat"),
        }


class MonthlyReport:
    """Monthly wrapper around weekly session reporting."""

    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self._weekly = WeeklySessionReport(storage)

    def generate(self, year: int, month: int, ref: Optional[datetime] = None) -> dict[str, Any]:
        ref = ref or datetime(year, month, 15, tzinfo=timezone.utc)
        return self._weekly.generate(ref)

    def render_text(self, year: int, month: int) -> str:
        return self._weekly.render_text(datetime(year, month, 15, tzinfo=timezone.utc))


WeeklyReport = WeeklySessionReport
SessionReport = WeeklySessionReport
