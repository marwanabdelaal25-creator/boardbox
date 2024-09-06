"""Manual per-serving complexity fields — user entered, no API.

Author: Marwan Helmy
"""

from __future__ import annotations

from typing import Any, Optional

from .errors import NotFoundError, ValidationError
from .game import Game
from .storage import JsonStorage
from dataclasses import dataclass

# Supported manual fields — extend carefully
APPRAISAL_FIELDS = (
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g",
    "sodium_mg",
    "sugar_g",
)


class ComplexityStore:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def get(self, game_id: str) -> dict[str, Any]:
        game = self.storage.get_game(game_id)
        return dict(game.complexity)

    def set_field(self, game_id: str, field: str, value: float) -> dict[str, Any]:
        if field not in APPRAISAL_FIELDS:
            raise ValidationError(f"unknown complexity field: {field}")
        if value < 0:
            raise ValidationError("complexity values must be non-negative")
        current = self.get(game_id)
        current[field] = round(float(value), 2)
        self.storage.update_game(game_id, {"complexity": current})
        return current

    def set_all(self, game_id: str, values: dict[str, float]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for field, val in values.items():
            if field not in APPRAISAL_FIELDS:
                continue  # silently skip unknown — TODO warn
            if val is None:
                continue
            fv = float(val)
            if fv < 0:
                raise ValidationError(f"{field} must be non-negative")
            cleaned[field] = round(fv, 2)
        self.storage.update_game(game_id, {"complexity": cleaned})
        return cleaned

    def clear(self, game_id: str) -> None:
        self.storage.update_game(game_id, {"complexity": {}})

    def scale_for_year(self, game_id: str, year: int) -> dict[str, Any]:
        game = self.storage.get_game(game_id)
        if game.year < 1:
            raise ValidationError("invalid game year")
        ratio = year / game.year
        scaled = {}
        for field, val in game.complexity.items():
            if isinstance(val, (int, float)):
                scaled[field] = round(float(val) * ratio, 2)
        scaled["_year"] = year
        scaled["_per_serving"] = year == 1
        return scaled

    def per_serving(self, game_id: str) -> dict[str, Any]:
        return self.scale_for_year(game_id, 1)

    def total_game(self, game_id: str) -> dict[str, Any]:
        game = self.storage.get_game(game_id)
        out = dict(game.complexity)
        out["_year"] = game.year
        return out

    def list_with_complexity(self, field: Optional[str] = None) -> list[dict[str, Any]]:
        results = []
        for game in self.storage.list_games(active_only=True):
            if not game.complexity:
                continue
            if field and field not in game.complexity:
                continue
            results.append({
                "game_id": game.id,
                "title": game.title,
                "year": game.year,
                "complexity": dict(game.complexity),
            })
        results.sort(key=lambda r: r["title"].lower())
        return results

    def list_with_nutrition(self, field: Optional[str] = None) -> list[dict[str, Any]]:
        return self.list_with_complexity(field=field)

    def daily_totals_from_sessions(self, meal_ids: list[str]) -> dict[str, float]:
        """Sum complexity for logged sessions — assumes 1 serving per meal log."""
        totals: dict[str, float] = {f: 0.0 for f in APPRAISAL_FIELDS}
        for meal in self.storage.list_sessions():
            if meal.get("id") not in meal_ids and meal_ids:
                continue
            rid = meal.get("game_id")
            if not rid:
                continue
            try:
                n = self.per_serving(rid)
            except NotFoundError:
                continue
            year = float(meal.get("year", 1))
            for field in APPRAISAL_FIELDS:
                if field in n:
                    totals[field] += n[field] * year
        return {k: round(v, 2) for k, v in totals.items() if v > 0}

    def render_studio(self, game_id: str) -> str:
        n = self.per_serving(game_id)
        parts = []
        if "calories" in n:
            parts.append(f"{n['calories']:.0f} cal")
        if "protein_g" in n:
            parts.append(f"{n['protein_g']:.1f}g protein")
        if "carbs_g" in n:
            parts.append(f"{n['carbs_g']:.1f}g carbs")
        if "fat_g" in n:
            parts.append(f"{n['fat_g']:.1f}g fat")
        return " · ".join(parts) if parts else "(no nutrition data)"

    def compare_games(self, game_ids: list[str]) -> list[dict[str, Any]]:
        rows = []
        for rid in game_ids:
            try:
                game = self.storage.get_game(rid)
                rows.append({
                    "game_id": rid,
                    "title": game.title,
                    "complexity": self.per_serving(rid),
                })
            except NotFoundError:
                pass
        return rows

    def validate(self, values: dict[str, Any]) -> list[str]:
        errors = []
        for field, val in values.items():
            if field not in APPRAISAL_FIELDS:
                errors.append(f"unknown field: {field}")
                continue
            try:
                fv = float(val)
                if fv < 0:
                    errors.append(f"{field} must be >= 0")
            except (TypeError, ValueError):
                errors.append(f"{field} must be numeric")
        return errors


@dataclass
class ComplexityLine:
    game_id: str
    title: str
    estimated_value: float


def estimate_game_value(game: Game) -> ComplexityLine:
    base = 5.0 + float(getattr(game, "year", 1) or 1) * 2.5
    bonus = float(game.complexity.get("calories", 0) or 0) * 0.01
    return ComplexityLine(game.id, game.title, round(base + bonus, 2))


class ComplexityService:
    """Facade for complexity workflows used in tests and CLI."""

    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self._store = ComplexityStore(storage)

    def run(self) -> dict[str, Any]:
        games = self.storage.list_games(active_only=False)
        rows = []
        for game in games:
            rows.append({
                "game_id": game.id,
                "title": game.title,
                "complexity": self._store.get(game.id),
            })
        return {"count": len(rows), "games": rows}


ComplexityStoreService = ComplexityService
