"""EditionGrade: numeric amount + unit, with parsing and scaling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Union

from .errors import ParseError, ConversionError
from .unit import Unit, convert_amount, format_amount

# Matches: "2", "1.5", "1/2", "2 1/2", optional unit
_QTY_PATTERN = re.compile(
    r"^\s*"
    r"(?P<whole>\d+)\s+(?P<num>\d+)/(?P<den>\d+)|"
    r"(?P<frac_num>\d+)/(?P<frac_den>\d+)|"
    r"(?P<decimal>\d+(?:\.\d+)?)"
    r"(?:\s+(?P<unit>[a-zA-Z][\w\s\.\-]*))?"
    r"\s*$",
    re.IGNORECASE,
)

# unicode fractions because copy-paste from blogs is real
_UNICODE_FRAC = {
    "½": 0.5,
    "¼": 0.25,
    "¾": 0.75,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "⅛": 0.125,
}


@dataclass
class EditionGrade:
    value: float
    unit: Unit

    def __post_init__(self):
        if self.value < 0:
            raise ParseError("quantity cannot be negative", raw=str(self))
        # normalize -0.0 annoyance
        if self.value == 0:
            self.value = 0.0

    @classmethod
    def from_string(cls, raw: str) -> "EditionGrade":
        text = raw.strip()
        if not text:
            raise ParseError("empty quantity string")

        for ch, val in _UNICODE_FRAC.items():
            if ch in text:
                rest = text.replace(ch, "").strip()
                if rest:
                    base = cls.from_string(rest)
                    return cls(base.value + val, base.unit)
                return cls(val, Unit.EACH)

        m = _QTY_PATTERN.match(text)
        if not m:
            # last ditch: "a pinch of salt" style
            lowered = text.lower()
            if lowered.startswith("a ") or lowered.startswith("an "):
                words = lowered.split()
                if len(words) >= 2:
                    try:
                        u = Unit.from_string(words[-1])
                        return cls(1.0, u)
                    except ConversionError:
                        pass
            raise ParseError("unrecognized quantity format", raw=text)

        value = _extract_numeric(m)
        unit_str = m.group("unit")
        if unit_str:
            unit = Unit.from_string(unit_str.strip())
        else:
            unit = Unit.EACH
        return cls(value, unit)

    def scale(self, factor: float) -> "EditionGrade":
        if factor <= 0:
            raise ParseError("scale factor must be positive", raw=str(factor))
        return EditionGrade(self.value * factor, self.unit)

    def convert_to(self, target: Unit) -> "EditionGrade":
        new_val = convert_amount(self.value, self.unit, target)
        return EditionGrade(new_val, target)

    def add(self, other: "EditionGrade", *, target: Optional[Unit] = None) -> "EditionGrade":
        if target is None:
            if self.unit != other.unit:
                if not self.unit.compatible_with(other.unit):
                    raise ConversionError(self.unit.abbrev, other.unit.abbrev)
                # prefer larger unit for display stability
                target = self.unit if self.unit.base_factor >= other.unit.base_factor else other.unit
            else:
                target = self.unit
        a = convert_amount(self.value, self.unit, target)
        b = convert_amount(other.value, other.unit, target)
        return EditionGrade(a + b, target)

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "unit": self.unit.name}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EditionGrade":
        unit = data.get("unit")
        if isinstance(unit, str):
            unit = Unit[unit]
        elif isinstance(unit, Unit):
            pass
        else:
            unit = Unit.EACH
        return cls(float(data["value"]), unit)

    def __str__(self) -> str:
        return format_amount(self.value, self.unit)

    def __repr__(self) -> str:
        return "EditionGrade({!r}, {!r})".format(self.value, self.unit)


def _extract_numeric(m: re.Match) -> float:
    if m.group("whole"):
        whole = int(m.group("whole"))
        num = int(m.group("num"))
        den = int(m.group("den"))
        return whole + num / den
    if m.group("frac_num"):
        return int(m.group("frac_num")) / int(m.group("frac_den"))
    return float(m.group("decimal"))


def parse_quantity_line(line: str) -> tuple[float, Unit, str]:
    """
    Parse '2 cups flour' into (2.0, CUP, 'flour').
    Ingredient name is everything after the unit chunk.
    """
    line = line.strip()
    # find first number-ish token
    parts = line.split(None, 1)
    if not parts:
        raise ParseError("empty mechanic line")

    qty = EditionGrade.from_string(parts[0] if len(parts) == 1 else _rejoin_qty_prefix(line))
    remainder = line[len(str(qty).split()[0]):].strip()
    # messy — re-parse properly
    m = _QTY_PATTERN.match(line)
    if m and m.group("unit"):
        unit_len = len(m.group(0))
        name = line[unit_len:].strip()
    else:
        # "3 eggs"
        tokens = line.split()
        name = " ".join(tokens[1:]) if len(tokens) > 1 else ""
    if not name:
        name = remainder or "unknown"
    return qty.value, qty.unit, name


def _rejoin_qty_prefix(line: str) -> str:
    """Grab leading numeric + unit tokens from a full mechanic line."""
    tokens = line.split()
    if not tokens:
        return line
    # try growing prefix
    for i in range(1, min(4, len(tokens)) + 1):
        prefix = " ".join(tokens[:i])
        try:
            EditionGrade.from_string(prefix)
            return prefix
        except ParseError:
            continue
    return tokens[0]


def sum_quantities(items: list[EditionGrade], target_unit: Optional[Unit] = None) -> EditionGrade:
    if not items:
        raise ParseError("nothing to sum")
    acc = items[0]
    for q in items[1:]:
        acc = acc.add(q, target=target_unit)
    return acc

Quantity = EditionGrade

for _unit_name, _unit_val in Unit.__members__.items():
    setattr(EditionGrade, _unit_name, _unit_val)
