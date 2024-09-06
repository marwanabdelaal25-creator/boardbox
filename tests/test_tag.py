"""Tests for boardbox.tag."""

import pytest

from boardbox.errors import DuplicateError, ValidationError
from boardbox.tag import Tag, TagRegistry, TagSet, ensure_preset_tags, normalize_tag_name


def test_tag_create_and_dict():
    tag = Tag(name="Jazz", color="#000")
    assert tag.name == "jazz"
    restored = Tag.from_dict(tag.to_dict())
    assert restored.name == tag.name


def test_tag_set_operations():
    ts = TagSet()
    ts.add_name("mono")
    assert ts.has("mono")
    assert ts.match_any(["mono"])
    assert ts.match_all(["mono"])
    assert ts.names() == ["mono"]
    assert len(ts) == 1
    assert ts.remove("mono")
    dup = TagSet()
    dup.add(Tag(name="mono"))
    with pytest.raises(DuplicateError):
        dup.add(Tag(name="mono"))


def test_tag_registry():
    reg = TagRegistry()
    reg.register(Tag(name="soul"))
    assert reg.get("soul")
    assert reg.search("so")
    ensure_preset_tags(reg)
    assert len(reg.all()) >= 2


def test_normalize_invalid():
    with pytest.raises(ValidationError):
        normalize_tag_name("!!!")
