"""Pantry inventory mechanicing.

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .errors import NotFoundError, ValidationError
from .game import parse_iso
from .storage import JsonStorage


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Bin:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    location: str = "room"
    notes: str = ""

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Bin":
        cid = kwargs.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(name=name, id=cid, **kwargs)


class BinRegistry:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def add_item(
        self,
        name: str,
        quantity: float = 1.0,
        unit: str = "",
        *,
        location: str = "bin",
        expires_at: Optional[str] = None,
        mechanic_id: Optional[str] = None,
    ) -> dict:
        if not name.strip():
            raise ValidationError("item name required")
        return self.storage.create_bin_item({
            "id": uuid.uuid4().hex[:12],
            "name": name.strip(),
            "quantity": quantity,
            "unit": unit,
            "location": location,
            "expires_at": expires_at,
            "mechanic_id": mechanic_id,
            "added_at": _utc_now(),
        })

    def list_items(self, location: Optional[str] = None) -> list[dict]:
        rows = self.storage.list_bin()
        if location:
            loc = location.lower()
            rows = [r for r in rows if r.get("location", "").lower() == loc]
        return rows

    def get_item(self, item_id: str) -> dict:
        return self.storage.get_bin_item(item_id)

    def update_quantity(self, item_id: str, quantity: float) -> dict:
        if quantity < 0:
            raise ValidationError("quantity cannot be negative")
        return self.storage.update_bin_item(item_id, {"quantity": quantity})

    def consume(self, item_id: str, amount: float) -> dict:
        item = self.get_item(item_id)
        current = float(item.get("quantity", 0))
        new_qty = max(0.0, current - amount)
        patch: dict[str, Any] = {"quantity": new_qty}
        if new_qty == 0:
            patch["depleted_at"] = _utc_now()
        return self.storage.update_bin_item(item_id, patch)

    def restock(self, item_id: str, amount: float) -> dict:
        item = self.get_item(item_id)
        current = float(item.get("quantity", 0))
        return self.storage.update_bin_item(item_id, {
            "quantity": current + amount,
            "restocked_at": _utc_now(),
        })

    def delete_item(self, item_id: str) -> None:
        self.storage.delete_bin_item(item_id)

    def find_by_name(self, name: str) -> list[dict]:
        needle = name.lower().strip()
        return [
            i for i in self.storage.list_bin()
            if needle in i.get("name", "").lower()
        ]

    def low_stock(self, threshold: float = 1.0) -> list[dict]:
        return [
            i for i in self.storage.list_bin()
            if float(i.get("quantity", 0)) <= threshold
        ]

    def expired(self, ref: Optional[datetime] = None) -> list[dict]:
        ref = ref or datetime.now(timezone.utc)
        out = []
        for item in self.storage.list_bin():
            exp = parse_iso(item.get("expires_at"))
            if exp and exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp and exp < ref:
                out.append(item)
        return out

    def summary(self) -> dict[str, Any]:
        items = self.storage.list_bin()
        by_location: dict[str, int] = {}
        total_qty = 0.0
        for item in items:
            loc = item.get("location", "unknown")
            by_location[loc] = by_location.get(loc, 0) + 1
            total_qty += float(item.get("quantity", 0))
        return {
            "total_items": len(items),
            "total_quantity": round(total_qty, 2),
            "by_location": by_location,
            "low_stock_count": len(self.low_stock()),
            "expired_count": len(self.expired()),
        }

    def match_game_mechanics(self, game_id: str) -> dict[str, list[str]]:
        """Check bin against a game — returns have / missing lists."""
        game = self.storage.get_game(game_id)
        bin_names = {i.get("name", "").lower() for i in self.storage.list_bin()}
        have = []
        missing = []
        for ing in game.mechanics:
            name = ing.name.lower()
            if any(name in p or p in name for p in bin_names):
                have.append(ing.name)
            else:
                missing.append(ing.name)
        return {"have": have, "missing": missing}

    def merge_duplicates(self, dry_run: bool = True) -> list[dict]:
        """Find bin rows with same name+unit — FIXME: fuzzy matching later."""
        seen: dict[tuple[str, str], dict] = {}
        merges = []
        for item in self.storage.list_bin():
            key = (item.get("name", "").lower(), item.get("unit", "").lower())
            if key in seen:
                merges.append({"keep": seen[key]["id"], "merge": item["id"], "name": item.get("name")})
                if not dry_run:
                    keep = seen[key]
                    new_qty = float(keep.get("quantity", 0)) + float(item.get("quantity", 0))
                    self.storage.update_bin_item(keep["id"], {"quantity": new_qty})
                    self.storage.delete_bin_item(item["id"])
            else:
                seen[key] = item
        return merges


BinMechanicer = BinRegistry
PantryMechanicer = BinRegistry
