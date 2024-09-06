"""Tests for boardbox.bins."""
from datetime import datetime, timedelta, timezone

import pytest

from boardbox.errors import NotFoundError, ValidationError
from boardbox.bins import BinMechanicer


def test_add_and_list(populated_storage):
    pt = BinMechanicer(populated_storage)
    item = pt.add_item("rice", 2.0, "lb", location="bins")
    assert item["name"] == "rice"
    assert pt.list_items(location="bins")


def test_add_empty_name_raises(populated_storage):
    pt = BinMechanicer(populated_storage)
    with pytest.raises(ValidationError):
        pt.add_item("  ")


def test_consume_and_restock(populated_storage):
    pt = BinMechanicer(populated_storage)
    item = pt.add_item("beans", 5.0, "can")
    updated = pt.consume(item["id"], 2.0)
    assert float(updated["quantity"]) == 3.0
    restocked = pt.restock(item["id"], 2.0)
    assert float(restocked["quantity"]) == 5.0


def test_consume_depletes(populated_storage):
    pt = BinMechanicer(populated_storage)
    item = pt.add_item("spice", 1.0, "tsp")
    updated = pt.consume(item["id"], 5.0)
    assert float(updated["quantity"]) == 0.0
    assert updated.get("depleted_at")


def test_update_quantity_bad(populated_storage):
    pt = BinMechanicer(populated_storage)
    item = pt.add_item("salt", 1.0, "cup")
    with pytest.raises(ValidationError):
        pt.update_quantity(item["id"], -1)


def test_delete_and_get(populated_storage):
    pt = BinMechanicer(populated_storage)
    item = pt.add_item("temp", 1.0, "each")
    pt.delete_item(item["id"])
    with pytest.raises(NotFoundError):
        pt.get_item(item["id"])


def test_find_by_name(populated_storage):
    pt = BinMechanicer(populated_storage)
    hits = pt.find_by_name("olive")
    assert hits


def test_low_stock(populated_storage):
    pt = BinMechanicer(populated_storage)
    pt.add_item("almost gone", 0.5, "cup")
    assert pt.low_stock(threshold=1.0)


def test_expired(populated_storage):
    pt = BinMechanicer(populated_storage)
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    item = pt.add_item("milk", 1, "gal", expires_at=old)
    exp = pt.expired()
    assert any(x["id"] == item["id"] for x in exp)


def test_summary(populated_storage):
    pt = BinMechanicer(populated_storage)
    s = pt.summary()
    assert "total_items" in s


def test_match_game_mechanics(populated_storage):
    pt = BinMechanicer(populated_storage)
    match = pt.match_game_mechanics("rec001")
    assert "have" in match and "missing" in match


def test_merge_duplicates_dry_and_apply(populated_storage):
    pt = BinMechanicer(populated_storage)
    pt.add_item("salt", 1, "tsp")
    pt.add_item("salt", 2, "tsp")
    merges = pt.merge_duplicates(dry_run=True)
    assert merges
    pt.merge_duplicates(dry_run=False)
