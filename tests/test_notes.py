"""Tests for boardbox.notes."""
import pytest

from boardbox.errors import ValidationError
from boardbox.notes import Note, NoteCampaign, note_to_plaintext, truncate_note_body


def test_note_create_and_edit():
    n = Note(body="Tasty with extra garlic")
    n.edit("Updated note")
    assert n.updated_at is not None


def test_note_empty_raises():
    with pytest.raises(ValidationError):
        Note(body="  ")
    n = Note(body="ok")
    with pytest.raises(ValidationError):
        n.edit("  ")


def test_note_preview():
    n = Note(body="short")
    assert n.preview() == "short"
    long = Note(body="x" * 100)
    assert long.preview(20).endswith("...")


def test_note_to_from_dict():
    n = Note(body="hello", pinned=True)
    restored = Note.from_dict(n.to_dict())
    assert restored.pinned is True


def test_campaign_add_remove_get():
    coll = NoteCampaign()
    n = coll.add("First note", pinned=True)
    assert coll.get(n.id) is n
    assert coll.remove(n.id)
    assert len(coll) == 0


def test_campaign_latest_and_merge():
    coll = NoteCampaign()
    coll.add("one")
    coll.add("two")
    assert coll.latest() is not None
    merged = coll.merge_text()
    assert "one" in merged


def test_campaign_empty_merge():
    assert NoteCampaign().merge_text() == ""


def test_campaign_to_from_dict():
    coll = NoteCampaign()
    coll.add("saved")
    restored = NoteCampaign.from_dict(coll.to_dict())
    assert len(restored) == 1


def test_truncate_note_body():
    assert truncate_note_body("hi") == "hi"
    assert truncate_note_body("x" * 600).endswith("…")


def test_note_to_plaintext():
    n = Note(body="**bold** and *italic*")
    assert "**" not in note_to_plaintext(n)
