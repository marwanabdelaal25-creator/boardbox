"""Compatibility alias — tests import studio metadata from publisher_name."""

from boardbox.publisher import (
    Publisher,
    PublisherRegion,
    PublisherRegistry,
    resolve_publisher_name,
    resolve_publisher_name_studio,
)

__all__ = [
    "Publisher",
    "PublisherRegion",
    "PublisherRegistry",
    "resolve_publisher_name",
    "resolve_publisher_name_studio",
]
