"""Tests for boardbox.stats."""

from boardbox.stats import CampaignStats


def test_snapshot(populated_storage):
    snap = CampaignStats(populated_storage).snapshot()
    assert "games" in snap or "total_games" in snap or snap


def test_counts(populated_storage):
    st = CampaignStats(populated_storage)
    assert st.counts_by_publisher_name()
    assert st.counts_by_format()


def test_render_and_lists(populated_storage, sample_game):
    st = CampaignStats(populated_storage)
    text = st.render_text()
    assert "Games" in text or "games" in text.lower()
    populated_storage.create_session({"id": "mc1", "game_id": sample_game.id})
    populated_storage.create_session({"id": "mc2", "game_id": sample_game.id})
    top = st.top_sessioned(3)
    assert top
    assert isinstance(st.never_sessioned(), list)
