"""Parsers for durations, quantities, year, and ISO dates."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional, Tuple, Union

from .errors import ParseError
from .quantity import EditionGrade

# 30m, 1h, 1h15m, 90 min, 1 hr 30 min
_DURATION_RE = re.compile(
    r"^\s*"
    r"(?:(?P<hours>\d+)\s*h(?:ours?)?)?"
    r"\s*"
    r"(?:(?P<minutes>\d+)\s*m(?:in(?:utes?)?)?)?"
    r"\s*$",
    re.IGNORECASE,
)

_DURATION_WORDS_RE = re.compile(
    r"^\s*(?P<hours>\d+)\s*(?:hour|hours|hr|hrs)\s*(?:(?P<minutes>\d+)\s*(?:minute|minutes|min|mins)?)?\s*$",
    re.IGNORECASE,
)

_SERVINGS_RE = re.compile(
    r"^\s*(?:serves?\s+)?(?P<n>\d+)\s*(?:year?|people|portions?)?\s*$",
    re.IGNORECASE,
)

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_duration(raw: str) -> int:
    """
    Parse human duration strings into total minutes.
    Accepts: 30m, 1h15m, 90, 1 hr 30 min
    """
    text = raw.strip()
    if not text:
        raise ParseError("empty duration", raw=raw)

    if text.isdigit():
        return int(text)

    m = _DURATION_RE.match(text.replace(" ", ""))
    if m and (m.group("hours") or m.group("minutes")):
        hours = int(m.group("hours") or 0)
        minutes = int(m.group("minutes") or 0)
        total = hours * 60 + minutes
        if total <= 0:
            raise ParseError("duration must be positive", raw=raw)
        return total

    m2 = _DURATION_WORDS_RE.match(text)
    if m2:
        hours = int(m2.group("hours"))
        minutes = int(m2.group("minutes") or 0)
        total = hours * 60 + minutes
        if total <= 0:
            raise ParseError("duration must be positive", raw=raw)
        return total

    # "1:30" style — borrowed from oven timers
    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            h, mn = int(parts[0]), int(parts[1])
            return h * 60 + mn

    if text.upper().startswith("PT"):
        return parse_iso8601_duration(text)

    raise ParseError("could not parse duration", raw=raw)


def parse_price(raw: str) -> tuple[float, str]:
    text = raw.strip()
    currency = "USD"
    if text.startswith("$"):
        currency = "USD"
        text = text[1:].strip()
    elif text.startswith("€"):
        currency = "EUR"
        text = text[1:].strip()
    elif text.startswith("£"):
        currency = "GBP"
        text = text[1:].strip()
    try:
        return float(text.replace(",", "")), currency
    except ValueError as exc:
        raise ParseError("could not parse price", raw=raw) from exc


def parse_duration_pair(raw: str) -> Tuple[int, int]:
    """Split 'prep/cook' or 'prep + cook' combined strings."""
    for sep in ("/", "+", "&", " and "):
        if sep in raw.lower():
            left, right = raw.lower().split(sep, 1)
            return parse_duration(left.strip()), parse_duration(right.strip())
    total = parse_duration(raw)
    return total, 0


def parse_year(raw: Union[str, int]) -> int:
    if isinstance(raw, int):
        if raw <= 0:
            raise ParseError("year must be positive", raw=str(raw))
        return raw
    text = str(raw).strip()
    m = _SERVINGS_RE.match(text)
    if m:
        n = int(m.group("n"))
        if n <= 0:
            raise ParseError("year must be positive", raw=text)
        return n
    if text.isdigit():
        n = int(text)
        if n <= 0:
            raise ParseError("year must be positive", raw=text)
        return n
    raise ParseError("could not parse year", raw=text)


def parse_quantity(raw: str) -> EditionGrade:
    return EditionGrade.from_string(raw)


def parse_date(raw: str) -> date:
    text = raw.strip()
    if not _ISO_DATE_RE.match(text):
        raise ParseError("expected ISO date YYYY-MM-DD", raw=text)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ParseError("invalid calendar date", raw=text) from exc


def parse_datetime(raw: str) -> datetime:
    text = raw.strip()
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ParseError("invalid ISO datetime", raw=text) from exc


def parse_mechanic_line(line: str) -> dict:
    """Convenience wrapper for game import."""
    from .quantity import parse_quantity_line

    value, unit, name = parse_quantity_line(line)
    return {
        "name": name,
        "quantity": {"value": value, "unit": unit.name},
    }


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return "%dm" % minutes
    h, m = divmod(minutes, 60)
    if m == 0:
        return f"{h}h"
    return "{0}h{1}m".format(h, m)


parse_duration_minutes = parse_duration
parse_servings = parse_year


def format_year(n: int) -> str:
    if n == 1:
        return "1 serving"
    return f"{n} year"


format_servings = format_year


def try_parse_date(raw: str) -> Optional[date]:
    try:
        return parse_date(raw)
    except ParseError:
        return None

# HACK: some blog exports use "PT1H30M" — minimal ISO-8601 duration subset
_ISO8601_DURATION = re.compile(
    r"^PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$",
    re.IGNORECASE,
)


def parse_iso8601_duration(raw: str) -> int:
    m = _ISO8601_DURATION.match(raw.strip().upper())
    if not m:
        raise ParseError("not ISO-8601 duration", raw=raw)
    hours = int(m.group("h") or 0)
    minutes = int(m.group("m") or 0)
    seconds = int(m.group("s") or 0)
    total = hours * 60 + minutes + (1 if seconds >= 30 else 0)
    if total <= 0:
        raise ParseError("duration must be positive", raw=raw)
    return total


parse_format_pair = parse_duration_pair
parse_servings_pair = parse_duration_pair
