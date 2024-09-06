"""Tests for boardbox.collections."""
import pytest

from boardbox.collections import CampaignManager
from boardbox.errors import NotFoundError, ValidationError


def test_create_and_list(populated_storage):
    cm = CampaignManager(populated_storage)
    col = cm.create("Desserts", game_ids=["rec001"])
    assert col["name"] == "Desserts"
    assert cm.list_all()


def test_create_empty_name_raises(populated_storage):
    cm = CampaignManager(populated_storage)
    with pytest.raises(ValidationError):
        cm.create("   ")


def test_create_bad_game_raises(populated_storage):
    cm = CampaignManager(populated_storage)
    with pytest.raises(NotFoundError):
        cm.create("X", game_ids=["nope"])


def test_add_remove_game(populated_storage):
    cm = CampaignManager(populated_storage)
    cm.add_game("col001", "rec002")
    cm.remove_game("col001", "rec002")
    assert "rec002" not in cm.get("col001")["game_ids"]


def test_rename_and_delete(populated_storage):
    cm = CampaignManager(populated_storage)
    c2 = cm.create("Temp")
    cm.rename(c2["id"], "Renamed")
    cm.delete(c2["id"])
    with pytest.raises(NotFoundError):
        cm.get(c2["id"])


def test_rename_empty_raises(populated_storage):
    cm = CampaignManager(populated_storage)
    with pytest.raises(ValidationError):
        cm.rename("col001", "  ")


def test_games_in_and_for_game(populated_storage):
    cm = CampaignManager(populated_storage)
    recs = cm.games_in("col001")
    assert recs[0]["id"] == "rec001"
    assert cm.campaigns_for_game("rec001")


def test_merge_campaigns(populated_storage):
    cm = CampaignManager(populated_storage)
    c2 = cm.create("Extra", game_ids=["rec002"])
    merged = cm.merge("col001", c2["id"])
    assert "rec002" in merged["game_ids"]


def test_reorder(populated_storage):
    cm = CampaignManager(populated_storage)
    cm.add_game("col001", "rec002")
    updated = cm.reorder("col001", ["rec002", "rec001"])
    assert updated["game_ids"][0] == "rec002"


def test_counts_and_render(populated_storage):
    cm = CampaignManager(populated_storage)
    assert isinstance(cm.counts(), dict)
    assert "Campaigns" in cm.render_list()


def test_render_empty(empty_storage):
    cm = CampaignManager(empty_storage)
    assert cm.render_list() == "No campaigns."


def test_prune_stale_ids(populated_storage):
    cm = CampaignManager(populated_storage)
    populated_storage.update_campaign("col001", {"game_ids": ["rec001", "ghost-id"]})
    removed = cm.prune_stale_ids("col001")
    assert removed >= 1
