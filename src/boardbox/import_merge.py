"""Merge imported games with deduplication.

Author: Marwan Helmy
"""

from __future__ import annotations

import json
import re
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

from .errors import ImportPipelineError, ValidationError
from .game import Game
from .storage import JsonStorage


def _normalize_title(title: str) -> str:
    t = title.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


class ImportMerger:
    DEFAULT_THRESHOLD = 0.85

    def __init__(self, storage: JsonStorage, similarity_threshold: float = DEFAULT_THRESHOLD):
        self.storage = storage
        self.threshold = similarity_threshold

    def find_duplicates(self, incoming: Game | dict) -> list[dict]:
        if isinstance(incoming, Game):
            title = incoming.title
            src_url = incoming.source_url
        else:
            title = str(incoming.get("title", ""))
            src_url = str(incoming.get("source_url", ""))
        matches = []
        for existing in self.storage.list_games(active_only=False):
            score = _title_similarity(title, existing.title)
            if score >= self.threshold:
                matches.append({
                    "game_id": existing.id,
                    "title": existing.title,
                    "score": round(score, 3),
                    "reason": "title_similarity",
                })
            elif src_url and existing.source_url and src_url == existing.source_url:
                matches.append({
                    "game_id": existing.id,
                    "title": existing.title,
                    "score": 1.0,
                    "reason": "source_url",
                })
        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    def _prepare_game(self, data: dict) -> dict:
        row = dict(data)
        if not row.get("id"):
            row["id"] = uuid.uuid4().hex[:12]
        if not row.get("title"):
            raise ValidationError("imported game missing title")
        row.setdefault("mechanics", [])
        row.setdefault("componentlist", [])
        row.setdefault("tag_ids", row.pop("tags", []))
        row.setdefault("year", 4)
        row.setdefault("archived", False)
        return row

    def merge_one(
        self,
        incoming: dict,
        *,
        strategy: str = "skip",  # skip | replace | keep_both
        target_id: Optional[str] = None,
    ) -> dict[str, Any]:
        if strategy not in ("skip", "replace", "keep_both"):
            raise ValidationError(f"unknown merge strategy: {strategy}")
        dupes = self.find_duplicates(incoming)
        if target_id:
            dupes = [d for d in dupes if d["game_id"] == target_id] or dupes

        prepared = self._prepare_game(incoming)

        if not dupes:
            created = self.storage.create_game(prepared)
            return {"action": "created", "game": created.to_dict(), "duplicates": []}

        top = dupes[0]
        if strategy == "skip":
            return {"action": "skipped", "game": None, "duplicates": dupes}

        if strategy == "replace":
            updated = self.storage.update_game(top["game_id"], prepared)
            return {"action": "replaced", "game": updated.to_dict(), "duplicates": dupes}

        if strategy == "keep_both":
            prepared["title"] = f"{prepared['title']} (imported)"
            prepared["id"] = uuid.uuid4().hex[:12]
            created = self.storage.create_game(prepared)
            return {"action": "created_copy", "game": created.to_dict(), "duplicates": dupes}

        raise ValidationError(f"unknown merge strategy: {strategy}")

    def merge_batch(
        self,
        games: list[dict],
        *,
        strategy: str = "skip",
    ) -> dict[str, Any]:
        results = {"created": 0, "skipped": 0, "replaced": 0, "errors": [], "details": []}
        for idx, row in enumerate(games):
            try:
                outcome = self.merge_one(row, strategy=strategy)
                action = outcome["action"]
                if action.startswith("created"):
                    results["created"] += 1
                elif action == "skipped":
                    results["skipped"] += 1
                elif action == "replaced":
                    results["replaced"] += 1
                results["details"].append(outcome)
            except (ValidationError, ImportPipelineError) as exc:
                results["errors"].append({"index": idx, "error": str(exc)})
        return results

    def load_json_file(self, path: str | Path) -> list[dict]:
        p = Path(path)
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ImportPipelineError(str(p), str(exc)) from exc
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            if "games" in raw:
                games = raw["games"]
                if isinstance(games, list):
                    return games
            if "title" in raw:
                return [raw]
        raise ImportPipelineError(str(p), "unrecognized json shape")

    def import_file(
        self,
        path: str | Path,
        *,
        strategy: str = "skip",
    ) -> dict[str, Any]:
        games = self.load_json_file(path)
        return self.merge_batch(games, strategy=strategy)

    def preview(self, path: str | Path) -> list[dict]:
        games = self.load_json_file(path)
        preview = []
        for row in games:
            title = row.get("title", "(untitled)")
            dupes = self.find_duplicates(row)
            preview.append({
                "title": title,
                "duplicate_count": len(dupes),
                "best_match": dupes[0] if dupes else None,
            })
        return preview

    def dedupe_existing(self, *, dry_run: bool = True) -> list[dict]:
        """Find duplicate pairs already in storage."""
        games = self.storage.list_games(active_only=False)
        pairs = []
        seen: set[tuple[str, str]] = set()
        for i, a in enumerate(games):
            for b in games[i + 1:]:
                score = _title_similarity(a.title, b.title)
                if score >= self.threshold:
                    key = tuple(sorted([a.id, b.id]))
                    if key not in seen:
                        seen.add(key)
                        pairs.append({
                            "a": {"id": a.id, "title": a.title},
                            "b": {"id": b.id, "title": b.title},
                            "score": round(score, 3),
                        })
        if not dry_run:
            pass  # FIXME: interactive merge UI
        return pairs
