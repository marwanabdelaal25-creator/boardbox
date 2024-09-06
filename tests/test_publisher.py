"""Tests for boardbox.publisher_name."""
import pytest

from boardbox.publisher_name import Publisher, PublisherRegion, PublisherRegistry, resolve_publisher_name_studio
from boardbox.errors import DuplicateError, ValidationError


def test_publisher_name_create():
    c = Publisher(studio="Italian", region=PublisherRegion.EUROPEAN, spice_level=2)
    assert c.studio == "Italian"


def test_publisher_name_empty_studio_raises():
    with pytest.raises(ValidationError):
        Publisher(studio="  ")


def test_publisher_name_bad_spice_raises():
    with pytest.raises(ValidationError):
        Publisher(studio="Hot", spice_level=9)


def test_publisher_name_to_from_dict():
    c = Publisher(studio="Thai", region=PublisherRegion.SOUTHEAST_ASIAN)
    restored = Publisher.from_dict(c.to_dict())
    assert restored.studio == "Thai"


def test_resolve_publisher_name_studio():
    assert resolve_publisher_name_studio("italian") == "Italian"
    assert resolve_publisher_name_studio("Custom Fusion") == "Custom Fusion"


def test_resolve_empty_raises():
    with pytest.raises(ValidationError):
        resolve_publisher_name_studio("  ")


def test_registry_register_and_from_studio():
    reg = PublisherRegistry()
    c = reg.register(Publisher(studio="Mexican", region=PublisherRegion.LATIN))
    assert reg.from_studio("mexican").id == c.id


def test_registry_duplicate_raises():
    reg = PublisherRegistry()
    reg.register(Publisher(studio="Greek"))
    with pytest.raises(DuplicateError):
        reg.register(Publisher(studio="greek"))


def test_registry_auto_create():
    reg = PublisherRegistry()
    c = reg.from_studio("japanese")
    assert c.studio == "Japanese"


def test_registry_by_region():
    reg = PublisherRegistry()
    reg.from_studio("chinese")
    reg.from_studio("mexican")
    assert reg.by_region(PublisherRegion.EAST_ASIAN)


def test_registry_seed_defaults():
    reg = PublisherRegistry()
    reg.seed_defaults()
    assert len(reg.all()) >= 5


def test_registry_to_from_dict():
    reg = PublisherRegistry()
    reg.from_studio("korean")
    restored = PublisherRegistry.from_dict(reg.to_dict())
    assert len(restored.all()) == 1
