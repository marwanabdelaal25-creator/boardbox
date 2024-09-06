"""Tests for boardbox.plugins."""
import pytest

from boardbox.errors import NotFoundError, ValidationError
from boardbox.plugins import PluginRegistry, BUILTIN_HOOKS


def test_register_and_emit(populated_storage):
    pr = PluginRegistry(populated_storage)
    pr.register_handler("before_session", "t", lambda **kw: 42)
    assert pr.emit("before_session") == [42]


def test_register_bad_hook(populated_storage):
    pr = PluginRegistry(populated_storage)
    with pytest.raises(ValidationError):
        pr.register_handler("bad_hook", "x", lambda: None)


def test_register_plugin_enable_disable(populated_storage):
    pr = PluginRegistry(populated_storage)
    p = pr.register_plugin("p1", "Test", ["before_import"], enabled=True)
    pr.disable(p["id"])
    pr.enable(p["id"])
    assert pr.get_plugin(p["id"])["enabled"] is True


def test_plugin_bad_hook_in_list(populated_storage):
    pr = PluginRegistry(populated_storage)
    with pytest.raises(ValidationError):
        pr.register_plugin("p2", "Bad", ["not_a_hook"])


def test_emit_handler_error(populated_storage):
    pr = PluginRegistry(populated_storage)
    pr.register_handler("after_session", "bad", lambda **kw: 1 / 0)
    out = pr.emit("after_session")
    assert out[0].get("error")


def test_unregister_handler(populated_storage):
    pr = PluginRegistry(populated_storage)
    pr.register_handler("on_scale", "rm", lambda: 1)
    assert pr.unregister_handler("on_scale", "rm") is True


def test_get_plugin_missing(populated_storage):
    pr = PluginRegistry(populated_storage)
    with pytest.raises(NotFoundError):
        pr.get_plugin("missing")


def test_hooks_for_plugin(populated_storage):
    pr = PluginRegistry(populated_storage)
    p = pr.register_plugin("p3", "Hooks", ["before_backup", "after_backup"])
    assert pr.hooks_for_plugin(p["id"]) == ["before_backup", "after_backup"]


def test_summary(populated_storage):
    pr = PluginRegistry(populated_storage)
    s = pr.summary()
    assert s["total"] >= 0
    assert set(s["registered_handlers"]) == set(BUILTIN_HOOKS)
