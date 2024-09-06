"""Search games by title, mechanic, or step text.

Author: Marwan Helmy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .game import Game
from .storage import JsonStorage


@dataclass
class SearchHit:
    kind: str
    id: str
    title: str
    snippet: str
    score: float
    match_field: str = ""


class CampaignSearch:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def _tokenize(self, query: str) -> list[str]:
        return [t for t in query.lower().split() if t]

    def _score_text(self, text: str, tokens: list[str]) -> float:
        if not tokens or not text:
            return 0.0
        lower = text.lower()
        hits = sum(1 for t in tokens if t in lower)
        return hits / len(tokens)

    def _game_blob(self, game: Game) -> dict[str, str]:
        title = game.title
        mechanics = " ".join(game.mechanic_names())
        componentlist = " ".join(game.step_texts())
        meta = " ".join([
            game.publisher_name,
            game.format,
            game.notes,
            " ".join(game.tag_ids),
            " ".join(game.seasonal_tags),
        ])
        return {
            "title": title,
            "mechanics": mechanics,
            "componentlist": componentlist,
            "all": " ".join([title, mechanics, componentlist, meta]),
        }

    def search_games(
        self,
        query: str,
        *,
        active_only: bool = True,
        field: Optional[str] = None,
    ) -> list[SearchHit]:
        tokens = self._tokenize(query)
        if not tokens:
            return []
        hits: list[SearchHit] = []
        for game in self.storage.list_games(active_only=active_only):
            blobs = self._game_blob(game)
            fields = [field] if field and field in blobs else list(blobs.keys())
            best_score = 0.0
            best_field = ""
            best_snippet = ""
            for fname in fields:
                score = self._score_text(blobs[fname], tokens)
                if score > best_score:
                    best_score = score
                    best_field = fname
                    best_snippet = blobs[fname][:140]
            if best_score > 0:
                hits.append(SearchHit(
                    kind="game",
                    id=game.id,
                    title=game.title,
                    snippet=best_snippet,
                    score=best_score,
                    match_field=best_field,
                ))
        hits.sort(key=lambda h: (h.score, h.title.lower()), reverse=True)
        return hits

    def search_by_mechanic(self, mechanic: str) -> list[SearchHit]:
        needle = mechanic.lower().strip()
        hits = []
        for game in self.storage.list_games(active_only=True):
            names = [n.lower() for n in game.mechanic_names()]
            if any(needle in n for n in names):
                matched = [n for n in game.mechanic_names() if needle in n.lower()]
                hits.append(SearchHit(
                    kind="game",
                    id=game.id,
                    title=game.title,
                    snippet=", ".join(matched)[:120],
                    score=1.0,
                    match_field="mechanics",
                ))
        hits.sort(key=lambda h: h.title.lower())
        return hits

    def search_notes(self, query: str) -> list[SearchHit]:
        tokens = self._tokenize(query)
        hits = []
        for note in self.storage.list_notes():
            blob = " ".join([note.get("title", ""), note.get("body", "")])
            score = self._score_text(blob, tokens)
            if score > 0:
                hits.append(SearchHit(
                    kind="note",
                    id=note.get("id", ""),
                    title=note.get("title", "note"),
                    snippet=(note.get("body") or "")[:120],
                    score=score,
                    match_field="notes",
                ))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits

    def search_all(self, query: str, limit: Optional[int] = None) -> list[SearchHit]:
        combined = self.search_games(query) + self.search_notes(query)
        combined.sort(key=lambda h: h.score, reverse=True)
        if limit:
            combined = combined[:limit]
        return combined

    def suggest_titles(self, prefix: str, limit: int = 8) -> list[str]:
        p = prefix.lower()
        titles = []
        for game in self.storage.list_games(active_only=True):
            if game.title.lower().startswith(p):
                titles.append(game.title)
        titles.sort()
        return titles[:limit]

    def to_dicts(self, hits: list[SearchHit]) -> list[dict[str, Any]]:
        return [
            {
                "kind": h.kind,
                "id": h.id,
                "title": h.title,
                "snippet": h.snippet,
                "score": h.score,
                "match_field": h.match_field,
            }
            for h in hits
        ]

    def filter_publisher_name(self, publisher_name: str) -> list[Game]:
        c = publisher_name.lower()
        return [
            r for r in self.storage.list_games(active_only=True)
            if r.publisher_name.lower() == c
        ]

    def filter_format(self, format: str) -> list[Game]:
        cat = format.lower()
        return [
            r for r in self.storage.list_games(active_only=True)
            if r.format.lower() == cat
        ]


GameSearch = CampaignSearch
RecipeSearch = CampaignSearch
