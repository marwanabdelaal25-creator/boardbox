"""Rollups from session / listening log data."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from .game import Game
from .play_log import ListeningSession
from .storage import JsonStorage


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _month_key(ts: str) -> str:
    return ts[:7] if ts else "unknown"


def _game_studio(alb: Game) -> str:
    return getattr(alb, "display_title", None) or alb.title


def _game_designer(alb: Game) -> str:
    ids = getattr(alb, "designer_ids", []) or []
    return ids[0] if ids else "Unknown"


class PlayStats:
    def __init__(self, games: list[Game], sessions: list[ListeningSession]):
        self.games = games
        self.sessions = sessions
        self._by_game: Counter[str] = Counter(s.game_id for s in sessions)

    def never_spun(self) -> list[Game]:
        spun = set(self._by_game.keys())
        return [a for a in self.games if a.id not in spun and not a.archived]

    def most_spun(self, limit: int = 10) -> list[tuple[Game, int]]:
        titles = {a.id: a for a in self.games}
        out = []
        for aid, count in self._by_game.most_common(limit):
            if aid in titles:
                out.append((titles[aid], count))
        return out


def sessions_by_month(storage: JsonStorage) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for session in storage.list_listening():
        ts = session.get("started_at") or session.get("played_at") or ""
        counts[_month_key(ts)] += 1
    return dict(sorted(counts.items()))


def most_spun_games(storage: JsonStorage, *, limit: int = 10) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for session in storage.list_listening():
        aid = session.get("game_id")
        if aid:
            counts[aid] += 1
    rows = []
    titles = {a.id: _game_studio(a) for a in storage.list_games(active_only=False)}
    for aid, n in counts.most_common(limit):
        rows.append({"game_id": aid, "title": titles.get(aid, aid), "sessions": n})
    return rows


def sessions_per_weekday(storage: JsonStorage) -> dict[str, int]:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts = [0] * 7
    for session in storage.list_listening():
        raw = session.get("started_at") or session.get("played_at") or ""
        dt = parse_iso(raw)
        if dt:
            counts[dt.weekday()] += 1
    return {names[i]: counts[i] for i in range(7)}


def designer_session_totals(storage: JsonStorage) -> dict[str, int]:
    by_game = {a.id: _game_designer(a) for a in storage.list_games(active_only=False)}
    totals: defaultdict[str, int] = defaultdict(int)
    for session in storage.list_listening():
        designer = by_game.get(session.get("game_id", ""), "Unknown")
        totals[designer] += 1
    return dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0])))


def summary_text(storage: JsonStorage, *, month: Optional[str] = None) -> str:
    sessions = storage.list_listening()
    if month:
        sessions = [
            s for s in sessions
            if _month_key(s.get("started_at") or s.get("played_at") or "") == month
        ]
    lines = ["Session summary: %d sessions" % len(sessions)]
    if sessions:
        top = most_spun_games(storage, limit=3)
        for row in top:
            lines.append("  • %s (%d)" % (row["title"], row["sessions"]))
        return "\n".join(lines)

    # TODO: export plays per month chart data
    return "\n".join(lines)


def sessions_per_hour(storage: JsonStorage) -> dict[int, int]:
    counts: Counter[int] = Counter()
    for session in storage.list_listening():
        raw = session.get("started_at") or session.get("played_at") or ""
        dt = parse_iso(raw)
        if dt:
            counts[dt.hour] += 1
    return dict(sorted(counts.items()))


def average_sessions_per_game(storage: JsonStorage) -> float:
    games = storage.list_games(active_only=False)
    if not games:
        return 0.0
    counts = Counter(s.get("game_id") for s in storage.list_sessions())
    total = sum(counts.get(a.id, 0) for a in games)
    return round(total / len(games), 2)


def dormant_games(storage: JsonStorage, *, days: int = 90) -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc)
    out = []
    for game in storage.list_games(active_only=True):
        raw = game.last_played_at
        dt = parse_iso(raw)
        if dt is None:
            out.append(game.to_dict())
            continue
        if (cutoff - dt.replace(tzinfo=timezone.utc)).days >= days:
            out.append(game.to_dict())
    return out


def genre_session_counts(storage: JsonStorage) -> dict[str, int]:
    genres: Counter[str] = Counter()
    game_genres = {
        a.id: getattr(a, "genres", None) or a.tag_ids or [a.publisher_name or "unknown"]
        for a in storage.list_games(active_only=False)
    }
    for session in storage.list_listening():
        aid = session.get("game_id")
        for g in game_genres.get(aid, []) or ["unknown"]:
            genres[g] += 1
    return dict(genres.most_common())


def format_session_report(storage: JsonStorage) -> str:
    lines = [
        "Games: %d" % storage.count_games(active_only=False),
        "Sessions logged: %d" % storage.count_sessions(),
        "Avg sessions/game: %.2f" % average_sessions_per_game(storage),
    ]
    top = most_spun_games(storage, limit=5)
    if top:
        lines.append("Top spun:")
        for row in top:
            lines.append("  %s — %d" % (row["title"], row["sessions"]))
    return "\n".join(lines)


def compare_months(storage: JsonStorage, a: str, b: str) -> dict[str, int]:
    """Return session counts for two YYYY-MM keys."""
    counts = sessions_by_month(storage)
    return {"a": counts.get(a, 0), "b": counts.get(b, 0), "delta": counts.get(b, 0) - counts.get(a, 0)}


def load_play_stats(storage: JsonStorage) -> PlayStats:
    games = storage.list_games(active_only=False)
    sessions = [ListeningSession.from_dict(s) for s in storage.list_listening()]
    return PlayStats(games, sessions)
