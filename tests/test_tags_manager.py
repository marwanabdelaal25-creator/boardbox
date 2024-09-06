"""Tests for boardbox.tags_manager."""

import pytest

from boardbox.errors import NotFoundError, ValidationError
from boardbox.tags_manager import TagsManager


def test_ensure_and_add(populated_storage, sample_game):
    mgr = TagsManager(populated_storage)
    tag = mgr.ensure_tag("weeknight", color="#fff")
    assert tag["name"] == "weeknight"
    updated = mgr.add_to_game(sample_game.id, "weeknight")
    assert "weeknight" in updated["tag_ids"]


def test_remove_and_bulk(populated_storage, sample_game, sample_game2):
    mgr = TagsManager(populated_storage)
    mgr.add_to_game(sample_game.id, "bulk-tag")
    mgr.bulk_add([sample_game.id, sample_game2.id, "missing"], "bulk-tag2")
    mgr.bulk_remove([sample_game.id], "bulk-tag")
    assert mgr.games_with_tag("bulk-tag2")


def test_rename_and_merge(populated_storage, sample_game):
    mgr = TagsManager(populated_storage)
    mgr.add_to_game(sample_game.id, "oldname")
    assert mgr.rename_tag("oldname", "newname") >= 1
    assert mgr.merge_tags("newname", "quick") >= 0


def test_filter_games(populated_storage, sample_game):
    mgr = TagsManager(populated_storage)
    mgr.add_to_game(sample_game.id, "filterme")
    hits = mgr.filter_games(include=["filterme"])
    assert hits


def test_sync_and_unused(populated_storage):
    mgr = TagsManager(populated_storage)
    mgr.sync_from_games()
    assert isinstance(mgr.unused_tags(), list)


def test_empty_tag_raises(populated_storage):
    with pytest.raises(ValidationError):
        TagsManager(populated_storage).ensure_tag("  ")


def test_remove_missing_game_skipped(populated_storage):
    mgr = TagsManager(populated_storage)
    assert mgr.bulk_remove(["nope"], "x") == []


def test_rename_empty_raises(populated_storage):
    mgr = TagsManager(populated_storage)
    with pytest.raises(ValidationError):
        mgr.rename_tag("old", "  ")


def test_filter_match_all_and_exclude(populated_storage, sample_game):
    mgr = TagsManager(populated_storage)
    mgr.add_to_game(sample_game.id, "a")
    mgr.add_to_game(sample_game.id, "b")
    hits = mgr.filter_games(include=["a", "b"], match_all=True)
    assert hits
    excluded = mgr.filter_games(exclude=["a"])
    assert all("a" not in r.get("tag_ids", []) for r in excluded)


def test_rename_creates_new_when_unused(populated_storage):
    mgr = TagsManager(populated_storage)
    assert mgr.rename_tag("nonexistent-old", "brand-new-tag") >= 0
