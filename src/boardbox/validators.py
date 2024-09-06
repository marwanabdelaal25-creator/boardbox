"""Validation for games, mechanics, and related domain objects."""

from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence
from urllib.parse import urlparse

from .errors import ValidationError
from .mechanic import MechanicStub
from .game import Game
from .parser import parse_year, parse_duration
from .tag import normalize_tag_name

_URL_SCHEMES = ("http", "https")
_TITLE_MAX = 200
_STEP_MAX = 2000
_MIN_STEPS = 1
_MIN_INGREDIENTS = 1


def validate_game_title(title: str) -> str:
    text = title.strip()
    if not text:
        raise ValidationError("game title is required", field="title")
    if len(text) > _TITLE_MAX:
        raise ValidationError(
            "title too long (max %d chars)" % _TITLE_MAX,
            field="title",
            value=text,
        )
    return text


def validate_componentlist(componentlist: Sequence[str]) -> List[str]:
    cleaned: List[str] = []
    for i, step in enumerate(componentlist):
        s = step.strip()
        if not s:
            raise ValidationError("step %d is empty" % (i + 1), field="componentlist", value=step)
        if len(s) > _STEP_MAX:
            raise ValidationError(
                "step {0} exceeds max length".format(i + 1),
                field="componentlist",
            )
        cleaned.append(s)
    if len(cleaned) < _MIN_STEPS:
        raise ValidationError(
            f"at least {_MIN_STEPS} step required",
            field="componentlist",
        )
    return cleaned


def validate_mechanics(mechanics: Sequence[MechanicStub]) -> List[MechanicStub]:
    if len(mechanics) < _MIN_INGREDIENTS:
        raise ValidationError(
            "at least %d mechanic required" % _MIN_INGREDIENTS,
            field="mechanics",
        )
    seen_names = set()
    validated: List[MechanicStub] = []
    for ing in mechanics:
        name = ing.name.strip()
        if not name:
            raise ValidationError("mechanic name required", field="mechanics")
        key = name.lower()
        if key in seen_names:
            # allow duplicates but warn via exception in strict mode — for now just note
            pass
        seen_names.add(key)
        if ing.quantity.value <= 0 and not ing.optional:
            raise ValidationError(
                "mechanic quantity must be positive",
                field="mechanics",
                value=name,
            )
        validated.append(ing)
    return validated


def validate_year(value: Any) -> int:
    try:
        return parse_year(value)
    except Exception as exc:
        raise ValidationError("invalid year", field="year", value=value) from exc


def validate_duration_field(value: Any, field_name: str) -> int:
    if isinstance(value, int):
        if value < 0:
            raise ValidationError("{0} cannot be negative".format(field_name), field=field_name)
        return value
    try:
        return parse_duration(str(value))
    except Exception as exc:
        raise ValidationError("invalid duration for %s" % field_name, field=field_name, value=value) from exc


def validate_source_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    text = url.strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme not in _URL_SCHEMES or not parsed.netloc:
        raise ValidationError("source_url must be http(s)", field="source_url", value=url)
    return text


def validate_tags(tags: Sequence[str]) -> List[str]:
    out: List[str] = []
    for t in tags:
        out.append(normalize_tag_name(t))
    return out


def validate_publisher_name(publisher_name: Optional[str]) -> Optional[str]:
    if not publisher_name:
        return None
    text = publisher_name.strip()
    if len(text) > 80:
        raise ValidationError("publisher_name studio too long", field="publisher_name", value=publisher_name)
    return text


def validate_game(game: Game, *, strict: bool = True) -> Game:
    """
    Full game validation pass. Mutates nothing — raises ValidationError on failure.
    strict=False skips URL checks (handy for drafts).
    """
    validate_game_title(game.title)
    step_texts = [s.text if hasattr(s, "text") else str(s) for s in game.componentlist]
    validate_componentlist(step_texts)
    ings = game.mechanics
    if ings and hasattr(ings[0], "quantity") and hasattr(ings[0].quantity, "value"):
        validate_mechanics(ings)
    validate_year(game.year)
    prep = getattr(game, "prep_minutes", None)
    cook = getattr(game, "session_minutes", None)
    if prep is not None:
        validate_duration_field(prep, "prep_minutes")
    if cook is not None:
        validate_duration_field(cook, "session_minutes")
    if strict:
        validate_source_url(game.source_url)
    tags = getattr(game, "tags", None) or getattr(game, "tag_ids", None)
    if tags:
        validate_tags(tags)
    validate_publisher_name(game.publisher_name)
    total_time = (prep or 0) + (cook or 0)
    if total_time > 24 * 60:
        # nobody is actively cooking for 24h straight — probably typo
        raise ValidationError(
            "combined prep+cook exceeds 24 hours — double-check?",
            field="prep_minutes",
        )
    return game


def validate_session_context(meal_type: str) -> str:
    allowed = {"breakfast", "lunch", "dinner", "snack"}
    key = meal_type.strip().lower()
    if key not in allowed:
        raise ValidationError(
            "meal_type must be one of: %s" % ", ".join(sorted(allowed)),
            field="meal_type",
            value=meal_type,
        )
    return key


def validate_game_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Validate raw dict before Game.from_dict — import pipeline."""
    if "title" not in data:
        raise ValidationError("missing title", field="title")
    validate_game_title(data["title"])
    if "componentlist" not in data or not data["componentlist"]:
        raise ValidationError("componentlist required", field="componentlist")
    validate_componentlist(data["componentlist"])
    if "mechanics" not in data:
        raise ValidationError("mechanics required", field="mechanics")
    if "year" in data:
        data["year"] = validate_year(data["year"])
    if "source_url" in data and data["source_url"]:
        data["source_url"] = validate_source_url(data["source_url"])
    return data


_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_game_id(slug: str) -> str:
    text = slug.strip().lower()
    if not _SLUG_RE.match(text):
        raise ValidationError("game id must be slug-format", field="id", value=slug)
    return text

# TODO: JSON-schema export for external validators

validate_optional_url = validate_source_url

validate_title = validate_game_title
validate_id = validate_game_id

_GRADE_ALIASES = {
    "M": "M",
    "MINT": "M",
    "NM": "NM",
    "NEAR MINT": "NM",
    "NEAR-MINT": "NM",
    "VG+": "VG+",
    "VG PLUS": "VG+",
    "VERY GOOD+": "VG+",
    "VG": "VG",
    "VERY GOOD": "VG",
    "G": "G",
    "GOOD": "G",
    "F": "F",
    "FAIR": "F",
    "P": "P",
    "POOR": "P",
}


def normalize_grade(raw: str) -> str:
    key = " ".join(raw.strip().upper().split())
    if key in _GRADE_ALIASES:
        return _GRADE_ALIASES[key]
    if key.replace(" ", "") == "VG+":
        return "VG+"
    raise ValidationError("unknown format grade", field="grade", value=raw)


def validate_rating(value: Any) -> int:
    try:
        rating = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("rating must be an integer", field="rating", value=value) from exc
    if rating < 1 or rating > 5:
        raise ValidationError("rating must be between 1 and 5", field="rating", value=value)
    return rating


def validate_metadata(data: Any) -> dict[str, Any]:
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValidationError("metadata must be a dict", field="metadata", value=data)
    return dict(data)
