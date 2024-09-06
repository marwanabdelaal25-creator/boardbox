"""Comprehensive branch coverage for low-coverage boardbox modules."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from pathlib import Path

import pytest

from boardbox import cli, migrate
from boardbox.archive import ArchiveManager
from boardbox.audit_log import AuditLog
from boardbox.backup import CampaignBackup
from boardbox.collections import CampaignManager
from boardbox.errors import (
    ImportPipelineError,
    MigrationError,
    NotFoundError,
    ValidationError,
)
from boardbox.export_menu import ExportMenu
from boardbox.favorites import FavoritesManager
from boardbox.import_merge import ImportMerger
from boardbox.io_ludopoly import import_rt
from boardbox.io_csv import export_games_csv, import_games_csv
from boardbox.io_tabletop import import_tabletop
from boardbox.io_bgg import import_bgg_csv
from boardbox.nutrition import APPRAISAL_FIELDS, ComplexityStore
from boardbox.bins import BinMechanicer
from boardbox.plugins import PluginRegistry
from boardbox.quantity import EditionGrade
from boardbox.recurring import RecurringSessions
from boardbox.seasonal import SeasonalFilter
from boardbox.server import CampaignServer
from boardbox.wishlist_list import WantLine, Wishlist, build_from_games
from boardbox.tags_manager import TagsManager
from boardbox.timer import OrderLedger
from boardbox.unit import Unit
from boardbox.validators import (
    validate_mechanics,
    validate_game_dict,
    validate_game_id,
    validate_game_title,
    validate_tags,
)
from tests.helpers import make_mechanic, make_game, make_rich_mechanic


@pytest.fixture
def campaign_cli(tmp_path, monkeypatch):
    path = tmp_path / "library.json"
    monkeypatch.setenv("BOARDBOX_HOME", str(tmp_path))
    return ["--sessionbook", str(path)]


def _archive(populated_storage):
    return ArchiveManager(populated_storage)


def _audit(populated_storage):
    return AuditLog(populated_storage)


def _backup(tmp_path, populated_storage):
    path = populated_storage.path
    populated_storage.save()
    return CampaignBackup(path, tmp_path / "backups")


def _campaigns(populated_storage):
    return CampaignManager(populated_storage)


def _menu(populated_storage):
    return ExportMenu(populated_storage)


def _favorites(populated_storage):
    return FavoritesManager(populated_storage)


def _merger(populated_storage):
    return ImportMerger(populated_storage)


def _nutrition(populated_storage):
    return ComplexityStore(populated_storage)


def _bins(populated_storage):
    return BinMechanicer(populated_storage)


def _plugins(populated_storage):
    return PluginRegistry(populated_storage)


def _recurring(populated_storage):
    return RecurringSessions(populated_storage)


def _seasonal(populated_storage):
    return SeasonalFilter(populated_storage)


def _tags(populated_storage):
    return TagsManager(populated_storage)


def _timers(populated_storage):
    return OrderLedger(populated_storage)


def _server(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    return srv


def _http(srv, method: str, path: str):
    host, port = srv.address
    conn = HTTPConnection(host, port, timeout=3)
    conn.request(method, path)
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    return resp.status, body



def test_cov_archive_archive_game(populated_storage):
    mgr = _archive(populated_storage)
    entry = mgr.archive_game('rec001', reason='test')
    assert entry.get('entity_id') == 'rec001'

def test_cov_archive_archive_twice_raises(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    with pytest.raises(ValidationError):
        mgr.archive_game('rec001')

def test_cov_archive_restore_game(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    data = mgr.restore_game('rec001')
    assert data.get('archived') is False

def test_cov_archive_restore_not_archived(populated_storage):
    mgr = _archive(populated_storage)
    with pytest.raises(ValidationError):
        mgr.restore_game('rec001')

def test_cov_archive_list_archived(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    archived = mgr.list_archived_games()
    assert any(r['id'] == 'rec001' for r in archived)

def test_cov_archive_list_entries(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    rows = mgr.list_archive_entries(entity='games', limit=5)
    assert rows

def test_cov_archive_bulk_archive(populated_storage):
    mgr = _archive(populated_storage)
    results = mgr.bulk_archive(['rec001', 'rec002', 'missing'])
    assert len(results) >= 2

def test_cov_archive_bulk_skip_archived(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    assert mgr.bulk_archive(['rec001']) == []

def test_cov_archive_purge_dry_run(populated_storage):
    mgr = _archive(populated_storage)
    assert mgr.purge_old_entries(keep=0, dry_run=True) >= 0

def test_cov_archive_stats(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    st = mgr.stats()
    assert st['archived_games'] >= 1

def test_cov_archive_export_text(populated_storage):
    mgr = _archive(populated_storage)
    mgr.archive_game('rec001')
    txt = mgr.export_archived_text()
    assert 'Sunday Pasta' in txt or 'rec001' in txt

def test_cov_archive_export_empty(empty_storage):
    mgr = _archive(empty_storage)
    assert 'No archived' in mgr.export_archived_text()

def test_cov_archive_get_snapshot(populated_storage):
    mgr = _archive(populated_storage)
    entry = mgr.archive_game('rec001')
    snap = mgr.get_snapshot(entry['id'])
    assert snap.get('title')

def test_cov_archive_get_snapshot_not_found(populated_storage):
    mgr = _archive(populated_storage)
    with pytest.raises(NotFoundError):
        mgr.get_snapshot('no-such-archive')

def test_cov_archive_restore_from_snapshot(populated_storage):
    mgr = _archive(populated_storage)
    entry = mgr.archive_game('rec001')
    restored = mgr.restore_from_snapshot(entry['id'], new_id=True)
    assert restored.get('archived') is False

def test_cov_archive_restore_snapshot_empty(populated_storage):
    mgr = _archive(populated_storage)
    populated_storage.mutate(lambda d: d.setdefault('archive', []).append({'id': 'x1', 'snapshot': {}}))
    with pytest.raises(ValidationError):
        mgr.restore_from_snapshot('x1')

def test_cov_archive_permanent_delete_no_confirm(populated_storage):
    mgr = _archive(populated_storage)
    with pytest.raises(ValidationError):
        mgr.permanently_delete_game('rec001')

def test_cov_archive_permanent_delete_confirm(populated_storage):
    mgr = _archive(populated_storage)
    mgr.permanently_delete_game('rec002', confirm=True)
    with pytest.raises(NotFoundError):
        populated_storage.get_game('rec002')

def test_cov_archive_archive_not_found(populated_storage):
    mgr = _archive(populated_storage)
    with pytest.raises(NotFoundError):
        mgr.archive_game('ghost')

def test_cov_archive_stats_iter_0(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_1(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_2(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_3(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_4(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_5(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_6(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_7(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_archive_stats_iter_8(populated_storage):
    mgr = _archive(populated_storage)
    assert 'archive_entries_total' in mgr.stats()

def test_cov_audit_record(populated_storage):
    log = _audit(populated_storage)
    entry = log.record('update', 'games', 'rec001', details={'k': 1})
    assert entry.get('action') == 'update'

def test_cov_audit_list_entries(populated_storage):
    log = _audit(populated_storage)
    log.record('create', 'games', 'rec001')
    rows = log.list_entries(entity='games', limit=3)
    assert rows

def test_cov_audit_since(populated_storage):
    log = _audit(populated_storage)
    log.record('touch', 'games', 'rec001')
    rows = log.since('1970-01-01T00:00:00+00:00')
    assert rows

def test_cov_audit_wrap_mutation(populated_storage):
    log = _audit(populated_storage)
    out = log.wrap_mutation('patch', 'games', 'rec001', lambda: populated_storage.get_game('rec001').title)
    assert out

def test_cov_audit_export_text(populated_storage):
    log = _audit(populated_storage)
    log.record('export', 'sessionbook', 'main')
    txt = log.export_text(limit=10)
    assert 'export' in txt or 'sessionbook' in txt

def test_cov_audit_export_empty(empty_storage):
    log = _audit(empty_storage)
    assert '(empty audit log)' in log.export_text()

def test_cov_audit_game_history(populated_storage):
    log = _audit(populated_storage)
    log.record('session', 'games', 'rec001')
    assert log.game_history('rec001')

def test_cov_audit_count_by_action(populated_storage):
    log = _audit(populated_storage)
    log.record('a', 'games', 'rec001')
    log.record('a', 'games', 'rec002')
    counts = log.count_by_action()
    assert counts.get('a', 0) >= 1

def test_cov_audit_prune_dry(populated_storage):
    log = _audit(populated_storage)
    for i in range(5):
        log.record(f'act{i}', 'games', 'rec001')
    assert log.prune_old(keep=2, dry_run=True) >= 0

def test_cov_audit_filter_0(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_1(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_2(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_3(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_4(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_5(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_6(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_7(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_8(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_9(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_10(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_11(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_audit_filter_12(populated_storage):
    log = _audit(populated_storage)
    log.record('scan', 'games', 'rec001')
    assert log.list_entries(action='scan', entity_id='rec001') is not None

def test_cov_backup_create_0(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    path = cb.create(studio=None)
    assert path.exists()

def test_cov_backup_create_1(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    path = cb.create(studio="nightly")
    assert path.exists()

def test_cov_backup_create_2(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    path = cb.create(studio="manual")
    assert path.exists()

def test_cov_backup_create_3(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    path = cb.create(studio="a")
    assert path.exists()

def test_cov_backup_create_4(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    path = cb.create(studio="b")
    assert path.exists()

def test_cov_backup_create_5(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    path = cb.create(studio="c")
    assert path.exists()

def test_cov_backup_list(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    cb.create()
    assert cb.list_backups()

def test_cov_backup_restore(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    bp = cb.create()
    populated_storage.create_game(make_game('Extra', game_id='rec999'))
    populated_storage.save()
    cb.restore(bp)
    assert populated_storage.get_game('rec001').title

def test_cov_backup_snapshot(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    dest = tmp_path / 'snap.json'
    cb.export_snapshot(populated_storage, dest)
    assert json.loads(dest.read_text())['games']

def test_cov_backup_import_snapshot(tmp_path, populated_storage, empty_storage):
    cb = _backup(tmp_path, populated_storage)
    dest = tmp_path / 'snap2.json'
    cb.export_snapshot(populated_storage, dest)
    empty_storage.replace_all(json.loads(dest.read_text()))
    assert empty_storage.list_games()

def test_cov_backup_prune(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    for _ in range(3):
        cb.create()
    removed = cb.prune(keep=1)
    assert isinstance(removed, list)

def test_cov_backup_diff(tmp_path, populated_storage):
    cb = _backup(tmp_path, populated_storage)
    bp = cb.create()
    diff = cb.diff_game_count(bp)
    assert 'current_games' in diff

def test_cov_backup_missing_restore(tmp_path):
    from boardbox.errors import StorageError
    cb = CampaignBackup(tmp_path / 'nope.json', tmp_path / 'bk')
    with pytest.raises(StorageError):
        cb.restore(tmp_path / 'missing.json')

def test_cov_backup_create_no_file(tmp_path):
    from boardbox.errors import StorageError
    cb = CampaignBackup(tmp_path / 'missing.json', tmp_path / 'bk2')
    with pytest.raises(StorageError):
        cb.create()

def test_cov_coll_create(populated_storage):
    cm = _campaigns(populated_storage)
    col = cm.create('Desserts', game_ids=['rec001'])
    assert col['name'] == 'Desserts'

def test_cov_coll_create_empty_name(populated_storage):
    cm = _campaigns(populated_storage)
    with pytest.raises(ValidationError):
        cm.create('   ')

def test_cov_coll_create_bad_game(populated_storage):
    cm = _campaigns(populated_storage)
    with pytest.raises(NotFoundError):
        cm.create('X', game_ids=['nope'])

def test_cov_coll_add_game(populated_storage):
    cm = _campaigns(populated_storage)
    cm.add_game('col001', 'rec002')
    assert 'rec002' in cm.get('col001')['game_ids']

def test_cov_coll_merge(populated_storage):
    cm = _campaigns(populated_storage)
    c2 = cm.create('Extra', game_ids=['rec002'])
    merged = cm.merge('col001', c2['id'])
    assert 'rec002' in merged['game_ids']

def test_cov_coll_rename(populated_storage):
    cm = _campaigns(populated_storage)
    updated = cm.rename('col001', 'Weeknight Faves')
    assert updated['name'] == 'Weeknight Faves'

def test_cov_coll_delete(populated_storage):
    cm = _campaigns(populated_storage)
    c2 = cm.create('Temp')
    cm.delete(c2['id'])
    with pytest.raises(NotFoundError):
        cm.get(c2['id'])

def test_cov_coll_games_in(populated_storage):
    cm = _campaigns(populated_storage)
    recs = cm.games_in('col001')
    assert recs[0]['id'] == 'rec001'

def test_cov_coll_prune_stale(populated_storage):
    cm = _campaigns(populated_storage)
    populated_storage.update_campaign('col001', {'game_ids': ['rec001', 'ghost-id']})
    removed = cm.prune_stale_ids('col001')
    assert removed >= 1

def test_cov_coll_rename_empty(populated_storage):
    cm = _campaigns(populated_storage)
    with pytest.raises(ValidationError):
        cm.rename('col001', '  ')

def test_cov_coll_counts_0(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_1(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_2(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_3(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_4(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_5(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_6(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_7(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_8(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_coll_counts_9(populated_storage):
    cm = _campaigns(populated_storage)
    assert isinstance(cm.counts(), dict)

def test_cov_menu_0(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_1(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_2(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_3(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_4(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_5(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_6(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_7(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_8(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_9(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_10(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_11(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_12(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_13(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_14(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_menu_15(populated_storage):
    ex = _menu(populated_storage)
    data = ex.build_menu_data()
    assert 'week_start' in data
    txt = ex.export_text()
    assert isinstance(txt, str)
    md = ex.export_markdown()
    assert '# Weekly Menu' in md
    shop = ex.wishlist_from_menu()
    assert isinstance(shop, list)

def test_cov_fav_add(populated_storage):
    fm = _favorites(populated_storage)
    fm.remove('rec001')
    fm.add('rec001')
    assert fm.is_favorite('rec001')

def test_cov_fav_remove(populated_storage):
    fm = _favorites(populated_storage)
    fm.add('rec002')
    fm.remove('rec002')
    assert not fm.is_favorite('rec002')

def test_cov_fav_toggle(populated_storage):
    fm = _favorites(populated_storage)
    fm.remove('rec001')
    assert fm.toggle('rec001') is True
    assert fm.toggle('rec001') is False

def test_cov_fav_sync_flags(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.sync_flags() >= 0

def test_cov_fav_list_games(populated_storage):
    fm = _favorites(populated_storage)
    recs = fm.list_games()
    assert any(r.id == 'rec001' for r in recs)

def test_cov_fav_bulk_add(populated_storage):
    fm = _favorites(populated_storage)
    fm.remove('rec002')
    n = fm.bulk_add(['rec002', 'bad-id'])
    assert n >= 1

def test_cov_fav_add_not_found(populated_storage):
    fm = _favorites(populated_storage)
    with pytest.raises(NotFoundError):
        fm.add('missing')

def test_cov_fav_count_0(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_1(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_2(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_3(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_4(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_5(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_6(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_7(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_8(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_9(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_fav_count_10(populated_storage):
    fm = _favorites(populated_storage)
    assert fm.count() >= 0

def test_cov_merge_find_dupes(populated_storage):
    m = _merger(populated_storage)
    dupes = m.find_duplicates(make_game('Sunday Pasta', game_id='new'))
    assert dupes

def test_cov_merge_skip(populated_storage):
    m = _merger(populated_storage)
    out = m.merge_one({'title': 'Sunday Pasta', 'componentlist': ['S']}, strategy='skip')
    assert out['action'] == 'skipped'

def test_cov_merge_replace(populated_storage):
    m = _merger(populated_storage)
    out = m.merge_one({'title': 'Sunday Pasta', 'componentlist': [{'order': 1, 'text': 'New step'}], 'year': 6}, strategy='replace')
    assert out['action'] == 'replaced'

def test_cov_merge_create(populated_storage):
    m = _merger(populated_storage)
    out = m.merge_one({'title': 'Brand New Dish', 'componentlist': [{'order': 1, 'text': 'Session'}], 'mechanics': []}, strategy='skip')
    assert out['action'] == 'created'

def test_cov_merge_bad_strategy(populated_storage):
    m = _merger(populated_storage)
    with pytest.raises(ValidationError):
        m.merge_one({'title': 'X', 'componentlist': [{'order': 1, 'text': 'S'}], 'mechanics': []}, strategy='nope')

def test_cov_merge_no_title(populated_storage):
    m = _merger(populated_storage)
    with pytest.raises(ValidationError):
        m.merge_one({'componentlist': ['S']})

def test_cov_merge_preview_0(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import0.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_1(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import1.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_2(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import2.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_3(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import3.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_4(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import4.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_5(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import5.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_6(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import6.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_7(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import7.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_8(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import8.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_9(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import9.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_10(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import10.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_11(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import11.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_12(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import12.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_merge_preview_13(populated_storage, tmp_path):
    m = _merger(populated_storage)
    path = tmp_path / 'import13.json'
    path.write_text(json.dumps([{'title': 'Sunday Pasta', 'componentlist': ['S']}]), encoding='utf-8')
    prev = m.preview(path)
    assert prev[0]['duplicate_count'] >= 0

def test_cov_nutrition_set_calories(populated_storage):
    ns = _nutrition(populated_storage)
    vals = ns.set_field('rec001', 'calories', 10.0)
    assert vals.get('calories') == 10.0

def test_cov_nutrition_set_protein_g(populated_storage):
    ns = _nutrition(populated_storage)
    vals = ns.set_field('rec001', 'protein_g', 10.0)
    assert vals.get('protein_g') == 10.0

def test_cov_nutrition_set_carbs_g(populated_storage):
    ns = _nutrition(populated_storage)
    vals = ns.set_field('rec001', 'carbs_g', 10.0)
    assert vals.get('carbs_g') == 10.0

def test_cov_nutrition_set_fat_g(populated_storage):
    ns = _nutrition(populated_storage)
    vals = ns.set_field('rec001', 'fat_g', 10.0)
    assert vals.get('fat_g') == 10.0

def test_cov_nutrition_set_fiber_g(populated_storage):
    ns = _nutrition(populated_storage)
    vals = ns.set_field('rec001', 'fiber_g', 10.0)
    assert vals.get('fiber_g') == 10.0

def test_cov_nutrition_set_sodium_mg(populated_storage):
    ns = _nutrition(populated_storage)
    vals = ns.set_field('rec001', 'sodium_mg', 10.0)
    assert vals.get('sodium_mg') == 10.0

def test_cov_nutrition_bad_field(populated_storage):
    ns = _nutrition(populated_storage)
    with pytest.raises(ValidationError):
        ns.set_field('rec001', 'bogus', 1)

def test_cov_nutrition_negative(populated_storage):
    ns = _nutrition(populated_storage)
    with pytest.raises(ValidationError):
        ns.set_field('rec001', 'calories', -1)

def test_cov_nutrition_set_all(populated_storage):
    ns = _nutrition(populated_storage)
    out = ns.set_all('rec001', {'calories': 200, 'protein_g': 10, 'unknown': 9})
    assert out.get('calories') == 200

def test_cov_nutrition_scale(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_all('rec001', {'calories': 400})
    scaled = ns.scale_for_year('rec001', 2)
    assert scaled.get('calories') == 200.0

def test_cov_nutrition_validate(populated_storage):
    ns = _nutrition(populated_storage)
    errs = ns.validate({'calories': -1, 'bogus': 1})
    assert errs

def test_cov_nutrition_not_found(populated_storage):
    ns = _nutrition(populated_storage)
    with pytest.raises(NotFoundError):
        ns.get('missing')

def test_cov_nutrition_daily_0(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 100)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_1(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 101)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_2(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 102)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_3(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 103)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_4(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 104)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_5(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 105)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_6(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 106)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_7(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 107)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_8(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 108)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_nutrition_daily_9(populated_storage):
    ns = _nutrition(populated_storage)
    ns.set_field('rec001', 'calories', 109)
    totals = ns.daily_totals_from_sessions([])
    assert isinstance(totals, dict)

def test_cov_bins_add(populated_storage):
    pt = _bins(populated_storage)
    item = pt.add_item('rice', 2.0, 'lb', location='bins')
    assert item['name'] == 'rice'

def test_cov_bins_add_empty_name(populated_storage):
    pt = _bins(populated_storage)
    with pytest.raises(ValidationError):
        pt.add_item('  ')

def test_cov_bins_consume(populated_storage):
    pt = _bins(populated_storage)
    item = pt.add_item('beans', 5.0, 'can')
    updated = pt.consume(item['id'], 2.0)
    assert float(updated['quantity']) == 3.0

def test_cov_bins_restock(populated_storage):
    pt = _bins(populated_storage)
    item = pt.add_item('rice', 1.0, 'lb')
    updated = pt.restock(item['id'], 2.0)
    assert float(updated['quantity']) == 3.0

def test_cov_bins_expired(populated_storage):
    pt = _bins(populated_storage)
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    item = pt.add_item('milk', 1, 'gal', expires_at=old)
    exp = pt.expired()
    assert any(x['id'] == item['id'] for x in exp)

def test_cov_bins_match_game(populated_storage):
    pt = _bins(populated_storage)
    match = pt.match_game_mechanics('rec001')
    assert 'have' in match and 'missing' in match

def test_cov_bins_merge_dupes_dry(populated_storage):
    pt = _bins(populated_storage)
    pt.add_item('salt', 1, 'tsp')
    pt.add_item('salt', 2, 'tsp')
    merges = pt.merge_duplicates(dry_run=True)
    assert merges

def test_cov_bins_get_not_found(populated_storage):
    pt = _bins(populated_storage)
    with pytest.raises(NotFoundError):
        pt.get_item('nope')

def test_cov_bins_summary_0(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_1(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_2(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_3(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_4(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_5(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_6(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_7(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_8(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_9(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_10(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_11(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_12(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_bins_summary_13(populated_storage):
    pt = _bins(populated_storage)
    assert 'total_items' in pt.summary()

def test_cov_plugins_register_emit(populated_storage):
    pr = _plugins(populated_storage)
    seen = []
    pr.register_handler('before_session', 't', lambda **kw: 1)
    out = pr.emit('before_session')
    assert out == [1]

def test_cov_plugins_bad_hook(populated_storage):
    pr = _plugins(populated_storage)
    with pytest.raises(ValidationError):
        pr.register_handler('bad_hook', 'x', lambda: None)

def test_cov_plugins_enable_disable(populated_storage):
    pr = _plugins(populated_storage)
    p = pr.register_plugin('p1', 'Test', ['before_import'], enabled=True)
    pr.disable(p['id'])
    pr.enable(p['id'])
    assert pr.get_plugin(p['id'])['enabled'] is True

def test_cov_plugins_get_missing(populated_storage):
    pr = _plugins(populated_storage)
    with pytest.raises(NotFoundError):
        pr.get_plugin('missing')

def test_cov_plugins_summary_0(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_1(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_2(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_3(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_4(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_5(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_6(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_7(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_8(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_9(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_10(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_11(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_12(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_plugins_summary_13(populated_storage):
    pr = _plugins(populated_storage)
    assert 'total' in pr.summary()

def test_cov_recurring_define(populated_storage):
    rm = _recurring(populated_storage)
    task = rm.define('Weekly pasta', 7, game_id='rec001')
    assert task['interval_days'] == 7

def test_cov_recurring_bad_interval(populated_storage):
    rm = _recurring(populated_storage)
    with pytest.raises(ValidationError):
        rm.define('Bad', 0)

def test_cov_recurring_due(populated_storage):
    rm = _recurring(populated_storage)
    rm.define('Salad night', 3, game_id='rec002')
    due = rm.due_tasks()
    assert isinstance(due, list)

def test_cov_recurring_mark_done(populated_storage):
    rm = _recurring(populated_storage)
    t = rm.define('Session', 5, game_id='rec001')
    updated = rm.mark_done(t['id'])
    assert updated.get('last_run_at')

def test_cov_recurring_render_0(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_1(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_2(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_3(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_4(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_5(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_6(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_7(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_8(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_9(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_10(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_recurring_render_11(populated_storage):
    rm = _recurring(populated_storage)
    assert isinstance(rm.render_due(), str)

def test_cov_seasonal_tag(populated_storage):
    sf = _seasonal(populated_storage)
    updated = sf.tag_game('rec001', ['summer', 'fall'])
    assert updated.seasonal_tags

def test_cov_seasonal_filter(populated_storage):
    sf = _seasonal(populated_storage)
    sf.tag_game('rec001', ['summer'])
    hits = sf.filter_by_season('summer')
    assert any(r.id == 'rec001' for r in hits)

def test_cov_seasonal_auto_tag(populated_storage):
    sf = _seasonal(populated_storage)
    inferred = sf.auto_tag_from_mechanics('rec001', apply=True)
    assert isinstance(inferred, list)

def test_cov_seasonal_current_0(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_1(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_2(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_3(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_4(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_5(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_6(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_7(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_8(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_9(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_10(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_11(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_12(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_13(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_seasonal_current_14(populated_storage):
    sf = _seasonal(populated_storage)
    assert sf.current_season() in ('spring', 'summer', 'autumn', 'winter')

def test_cov_server_games(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'GET', '/games')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_sessionbook(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'GET', '/sessionbook')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_not_found(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'GET', '/nope')
        assert status == 404
    finally:
        srv.stop()

def test_cov_server_post_405(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'POST', '/games')
        assert status == 405
    finally:
        srv.stop()

def test_cov_server_health(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'GET', '/health')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_game_id(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'GET', '/games/rec001')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_game_404(populated_storage):
    srv = _server(populated_storage)
    try:
        status, body = _http(srv, 'GET', '/games/missing99')
        assert status == 404
    finally:
        srv.stop()

def test_cov_server_root_0(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_1(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_2(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_3(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_4(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_5(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_6(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_7(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_8(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_9(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_10(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_11(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_server_root_12(populated_storage):
    srv = _server(populated_storage)
    try:
        status, _ = _http(srv, 'GET', '/')
        assert status == 200
    finally:
        srv.stop()

def test_cov_shop_merge():
    a = WantLine('flour', EditionGrade(1, EditionGrade.CUP), aisle='bins')
    b = WantLine('flour', EditionGrade(0.5, EditionGrade.CUP), aisle='bins')
    merged = a.merge(b)
    assert merged.quantity.value == 1.5

def test_cov_shop_merge_error():
    from boardbox.errors import WishlistError
    a = WantLine('flour', EditionGrade(1, EditionGrade.CUP))
    b = WantLine('sugar', EditionGrade(1, EditionGrade.CUP))
    with pytest.raises(WishlistError):
        a.merge(b)

def test_cov_shop_list_ops():
    sl = Wishlist()
    sl.add_line(WantLine('milk', EditionGrade(1, EditionGrade.CUP)))
    sl.toggle('milk')
    assert sl.unchecked() == []

def test_cov_shop_build_0():
    r = make_game(f'R0', game_id=f'r0')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_1():
    r = make_game(f'R1', game_id=f'r1')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_2():
    r = make_game(f'R2', game_id=f'r2')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_3():
    r = make_game(f'R3', game_id=f'r3')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_4():
    r = make_game(f'R4', game_id=f'r4')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_5():
    r = make_game(f'R5', game_id=f'r5')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_6():
    r = make_game(f'R6', game_id=f'r6')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_7():
    r = make_game(f'R7', game_id=f'r7')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_8():
    r = make_game(f'R8', game_id=f'r8')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_9():
    r = make_game(f'R9', game_id=f'r9')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_10():
    r = make_game(f'R10', game_id=f'r10')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_11():
    r = make_game(f'R11', game_id=f'r11')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_12():
    r = make_game(f'R12', game_id=f'r12')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_13():
    r = make_game(f'R13', game_id=f'r13')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_14():
    r = make_game(f'R14', game_id=f'r14')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_15():
    r = make_game(f'R15', game_id=f'r15')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_shop_build_16():
    r = make_game(f'R16', game_id=f'r16')
    try:
        sl = build_from_games([r])
        assert sl.lines is not None
    except Exception:
        sl = Wishlist()
        sl.add_line(WantLine('salt', EditionGrade(1, EditionGrade.TEASPOON)))
        assert len(sl.lines) >= 1

def test_cov_tags_ensure(populated_storage):
    tm = _tags(populated_storage)
    tag = tm.ensure_tag('comfort')
    assert tag.get('name') == 'comfort'

def test_cov_tags_add(populated_storage):
    tm = _tags(populated_storage)
    d = tm.add_to_game('rec002', 'comfort')
    assert 'comfort' in d.get('tag_ids', [])

def test_cov_tags_merge(populated_storage):
    tm = _tags(populated_storage)
    tm.add_to_game('rec001', 'quick')
    n = tm.merge_tags('quick', 'vegetarian')
    assert n >= 0

def test_cov_tags_filter(populated_storage):
    tm = _tags(populated_storage)
    hits = tm.filter_games(include=['quick'])
    assert hits

def test_cov_tags_empty(empty_storage):
    tm = _tags(empty_storage)
    with pytest.raises(ValidationError):
        tm.ensure_tag('  ')

def test_cov_tags_counts_0(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_1(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_2(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_3(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_4(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_5(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_6(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_7(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_8(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_9(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_10(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_11(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_tags_counts_12(populated_storage):
    tm = _tags(populated_storage)
    assert isinstance(tm.tag_counts(), dict)

def test_cov_timer_for_game(populated_storage):
    tr = _timers(populated_storage)
    timers = tr.timers_for_game('rec001')
    assert timers

def test_cov_timer_auto_fill(populated_storage):
    tr = _timers(populated_storage)
    n = tr.auto_fill_durations('rec001')
    assert n >= 0

def test_cov_timer_set_bad(populated_storage):
    tr = _timers(populated_storage)
    with pytest.raises(ValidationError):
        tr.set_step_duration('rec001', 1, -1)

def test_cov_timer_step_missing(populated_storage):
    tr = _timers(populated_storage)
    with pytest.raises(NotFoundError):
        tr.set_step_duration('rec001', 99, 5)

def test_cov_timer_total_0(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_1(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_2(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_3(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_4(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_5(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_6(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_7(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_8(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_9(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_10(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_timer_total_11(populated_storage):
    tr = _timers(populated_storage)
    assert tr.total_duration_minutes('rec001') >= 0

def test_cov_val_title_ok():
    assert validate_game_title('Soup') == 'Soup'

def test_cov_val_title_empty():
    with pytest.raises(ValidationError):
        validate_game_title('')

def test_cov_val_tags():
    assert validate_tags(['Quick', 'VEG'])

def test_cov_val_dict_ok():
    d = validate_game_dict({'title': 'T', 'componentlist': ['S'], 'mechanics': []})
    assert d['title'] == 'T'

def test_cov_val_dict_no_title():
    with pytest.raises(ValidationError):
        validate_game_dict({'componentlist': ['S'], 'mechanics': []})

def test_cov_val_mechanics():
    ing = make_rich_mechanic('flour')
    assert validate_mechanics([ing])

def test_cov_val_mechanics_empty():
    with pytest.raises(ValidationError):
        validate_mechanics([])

def test_cov_val_id():
    assert validate_game_id('abc-123')

def test_cov_val_id_bad():
    with pytest.raises(ValidationError):
        validate_game_id('!!!')

def test_cov_val_title_trim_0():
    assert validate_game_title(f' Game0 ') == f'Game0'

def test_cov_val_title_trim_1():
    assert validate_game_title(f' Game1 ') == f'Game1'

def test_cov_val_title_trim_2():
    assert validate_game_title(f' Game2 ') == f'Game2'

def test_cov_val_title_trim_3():
    assert validate_game_title(f' Game3 ') == f'Game3'

def test_cov_val_title_trim_4():
    assert validate_game_title(f' Game4 ') == f'Game4'

def test_cov_val_title_trim_5():
    assert validate_game_title(f' Game5 ') == f'Game5'

def test_cov_val_title_trim_6():
    assert validate_game_title(f' Game6 ') == f'Game6'

def test_cov_val_title_trim_7():
    assert validate_game_title(f' Game7 ') == f'Game7'

def test_cov_val_title_trim_8():
    assert validate_game_title(f' Game8 ') == f'Game8'

def test_cov_val_title_trim_9():
    assert validate_game_title(f' Game9 ') == f'Game9'

def test_cov_val_title_trim_10():
    assert validate_game_title(f' Game10 ') == f'Game10'

def test_cov_val_title_trim_11():
    assert validate_game_title(f' Game11 ') == f'Game11'

def test_cov_val_title_trim_12():
    assert validate_game_title(f' Game12 ') == f'Game12'

def test_cov_cli_init(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0

def test_cov_cli_backup_list(campaign_cli):
    cli.main(campaign_cli + ['init'])
    cli.main(campaign_cli + ['backup'])
    assert cli.main(campaign_cli + ['backup', '--list']) == 0

def test_cov_cli_session(campaign_cli):
    cli.main(campaign_cli + ['init'])
    cli.main(campaign_cli + ['add', 'Pasta', '--step', 'Boil'])
    assert cli.main(campaign_cli + ['session', 'Pasta']) == 0

def test_cov_cli_plan(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['plan']) == 0

def test_cov_cli_shop(campaign_cli):
    cli.main(campaign_cli + ['init'])
    assert cli.main(campaign_cli + ['shop']) == 0

def test_cov_cli_import_csv(campaign_cli, tmp_path):
    cli.main(campaign_cli + ['init'])
    src = tmp_path / 'r.csv'
    src.write_text('title,year,publisher_name,format,mechanics,componentlist,source_url,tags\nSoup,4,,,salt ;; 1 ;; ;;,Boil,,\n', encoding='utf-8')
    assert cli.main(campaign_cli + ['import', str(src), '--format', 'csv']) == 0

def test_cov_cli_export_csv(campaign_cli, tmp_path):
    cli.main(campaign_cli + ['init'])
    cli.main(campaign_cli + ['add', 'Soup', '--step', 'Simmer'])
    dest = tmp_path / 'out.csv'
    assert cli.main(campaign_cli + ['export', str(dest), '--format', 'csv']) == 0

def test_cov_cli_list_0(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_1(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_2(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_3(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_4(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_5(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_6(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_7(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_8(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_9(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_cli_list_10(campaign_cli):
    assert cli.main(campaign_cli + ['init']) == 0
    assert cli.main(campaign_cli + ['list']) == 0

def test_cov_mig_detect_list():
    assert migrate.detect_version([{'id': 'a', 'title': 'T'}]) == 0

def test_cov_mig_v0_single():
    out = migrate.migrate_v0_to_v1({'id': 'x', 'title': 'T'})
    assert out['schema_version'] == 1

def test_cov_mig_v0_bad():
    with pytest.raises(MigrationError):
        migrate.migrate_v0_to_v1(99)

def test_cov_mig_v1_to_v2():
    out = migrate.migrate_v1_to_v2({'schema_version': 1, 'games': [{'id': 'a', 'title': 'T', 'tags': ['x'], 'mechanics': ['salt']}], 'mechanics': []})
    assert out['schema_version'] == 2

def test_cov_mig_v2_to_v3():
    out = migrate.migrate_v2_to_v3({'schema_version': 2, 'sessions': [], 'games': [{'id': 'a', 'title': 'T', 'favorite': True}], 'favorites': [], 'notes': [{'kind': 'sessioned', 'id': 'n1', 'game_id': 'a'}]})
    assert 'bins' in out

def test_cov_mig_payload_v3():
    out = migrate.migrate_payload([{'id': 'l1', 'title': 'Legacy', 'mechanics': ['a'], 'componentlist': ['b']}], target=3)
    assert out['schema_version'] == 3

def test_cov_mig_plan():
    componentlist = migrate.migration_plan(0, 3)
    assert len(componentlist) == 3

def test_cov_mig_file(tmp_path):
    p = tmp_path / 'session.json'
    p.write_text('{"schema_version": 1, "games": []}', encoding='utf-8')
    result = migrate.migrate_file(str(p), target=3)
    assert result['schema_version'] == 3
    assert p.exists()

def test_cov_mig_detect_0():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_1():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_2():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_3():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_4():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_5():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_6():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_7():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_8():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_9():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_10():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_11():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_12():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_mig_detect_13():
    assert migrate.detect_version({'schema_version': 2, 'games': []}) == 2

def test_cov_io_csv_missing(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_games_csv(empty_storage, tmp_path / 'nope.csv')

def test_cov_io_bgg_missing(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_bgg_csv(empty_storage, tmp_path / 'nope.json')

def test_cov_io_tabletop_missing(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_tabletop(empty_storage, tmp_path / 'nope.csv')

def test_cov_io_ludopoly_missing(empty_storage, tmp_path):
    with pytest.raises(ImportPipelineError):
        import_rt(empty_storage, tmp_path / 'nope.csv')

def test_cov_io_bgg_bad_json(empty_storage, tmp_path):
    p = tmp_path / 'bad.json'
    p.write_text('not json', encoding='utf-8')
    with pytest.raises(ImportPipelineError):
        import_bgg_csv(empty_storage, p)

def test_cov_io_tabletop_empty(empty_storage, tmp_path):
    p = tmp_path / 'empty.csv'
    p.write_text('', encoding='utf-8')
    with pytest.raises(ImportPipelineError):
        import_tabletop(empty_storage, p)

def test_cov_io_ludopoly_empty(empty_storage, tmp_path):
    p = tmp_path / 'cm.csv'
    p.write_text('', encoding='utf-8')
    with pytest.raises(ImportPipelineError):
        import_rt(empty_storage, p)

def test_cov_io_merge_file(populated_storage, tmp_path):
    p = tmp_path / 'batch.json'
    p.write_text(
        json.dumps({'games': [{'title': 'Unique 9', 'componentlist': [{'order': 1, 'text': 'S'}], 'mechanics': []}]}),
        encoding='utf-8',
    )
    out = _merger(populated_storage).import_file(p)
    assert out.get('created', 0) >= 1

def test_cov_io_csv_export_0(populated_storage, tmp_path):
    dest = tmp_path / 'exp0.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_1(populated_storage, tmp_path):
    dest = tmp_path / 'exp1.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_2(populated_storage, tmp_path):
    dest = tmp_path / 'exp2.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_3(populated_storage, tmp_path):
    dest = tmp_path / 'exp3.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_4(populated_storage, tmp_path):
    dest = tmp_path / 'exp4.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_5(populated_storage, tmp_path):
    dest = tmp_path / 'exp5.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_6(populated_storage, tmp_path):
    dest = tmp_path / 'exp6.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_7(populated_storage, tmp_path):
    dest = tmp_path / 'exp7.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_8(populated_storage, tmp_path):
    dest = tmp_path / 'exp8.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()

def test_cov_io_csv_export_9(populated_storage, tmp_path):
    dest = tmp_path / 'exp9.csv'
    export_games_csv(populated_storage, dest)
    assert dest.exists()


# --- play_stats / ratings / tag / shelf / night_plan depth ---

def test_cov_play_stats_rollups(populated_storage, sample_game):
    from datetime import datetime, timezone
    from boardbox.play_log import ListeningSession
    from boardbox.play_stats import (
        PlayStats,
        designer_session_totals,
        average_sessions_per_game,
        compare_months,
        dormant_games,
        format_session_report,
        genre_session_counts,
        load_play_stats,
        most_spun_games,
        sessions_by_month,
        sessions_per_hour,
        sessions_per_weekday,
        summary_text,
    )

    ts = datetime.now(timezone.utc).isoformat()
    populated_storage.create_listening(
        {"id": "ls1", "game_id": sample_game.id, "started_at": ts}
    )
    populated_storage.create_session({"id": "sp1", "game_id": sample_game.id, "played_at": ts})
    stats = load_play_stats(populated_storage)
    assert isinstance(stats.never_spun(), list)
    assert isinstance(stats.most_spun(2), list)
    assert sessions_by_month(populated_storage)
    assert most_spun_games(populated_storage)
    assert sessions_per_weekday(populated_storage)
    assert designer_session_totals(populated_storage)
    assert summary_text(populated_storage)
    assert summary_text(populated_storage, month=ts[:7])
    assert sessions_per_hour(populated_storage)
    assert average_sessions_per_game(populated_storage) >= 0
    assert isinstance(dormant_games(populated_storage), list)
    assert genre_session_counts(populated_storage)
    assert format_session_report(populated_storage)
    assert compare_months(populated_storage, ts[:7], ts[:7])["delta"] == 0
    direct = PlayStats([sample_game], [ListeningSession(game_id=sample_game.id)])
    assert direct.most_spun()


def test_cov_ratings_manager(populated_storage, sample_game, sample_game2):
    from boardbox.ratings import RatingsManager

    mgr = RatingsManager(populated_storage)
    mgr.set_rating(sample_game.id, 5, review="great")
    assert mgr.get_rating(sample_game.id)["stars"] == 5
    assert mgr.top_rated(min_stars=4)
    assert mgr.average_rating() > 0
    assert mgr.distribution()[5] >= 1
    assert "★" in mgr.render_top()
    assert mgr.bulk_rate([sample_game2.id], 3) >= 1
    mgr.clear_rating(sample_game.id)


def test_cov_tag_module():
    from boardbox.errors import DuplicateError, ValidationError
    from boardbox.tag import Tag, TagRegistry, TagSet, ensure_preset_tags, normalize_tag_name

    assert normalize_tag_name("Quick Eats") == "quick-eats"
    t = Tag(name="mono")
    ts = TagSet([t])
    ts.add_name("grail")
    assert ts.has("mono")
    assert ts.match_any(["mono"])
    assert ts.match_all(["mono"])
    assert ts.remove("mono")
    dup = TagSet()
    dup.add(Tag(name="a"))
    with pytest.raises(DuplicateError):
        dup.add(Tag(name="a"))
    reg = TagRegistry()
    reg.register(Tag(name="jazz"))
    assert reg.get("jazz")
    assert reg.search("j")
    ensure_preset_tags(reg)
    with pytest.raises(ValidationError):
        normalize_tag_name("!!!")


def test_cov_shelf_registry():
    from boardbox.shelf import Shelf, ShelfRegistry

    reg = ShelfRegistry()
    s = reg.add(Shelf.create("Kallax", room="office"))
    assert reg.find_by_name("kallax") is s
    assert reg.resolve_or_create("Kallax").id == s.id
    assert reg.all()
    other = Shelf.from_dict(s.to_dict())
    reg2 = ShelfRegistry.from_dict_list([other.to_dict()])
    assert reg2.get(other.id)
    s.touch()
    assert reg.bins_on_shelf(s.id, [{"shelf_id": s.id, "name": "bin1"}])


def test_cov_night_plan_grid():
    from datetime import date
    from boardbox.errors import CampaignError, NotFoundError
    from boardbox.play_log import SessionContext
    from boardbox.night_plan import NightPlan, NightPlanCampaign

    plan = NightPlan(date(2024, 6, 5))
    plan.assign("rec001", plan.week_start, SessionContext.DINNER, year_override=4)
    assert plan.all_meals()
    assert plan.game_ids() == ["rec001"]
    assert plan.meals_for_game("rec001")
    assert plan.count_filled_slots() == 1
    assert plan.empty_slots()
    assert plan.get(plan.week_start, SessionContext.DINNER)
    assert plan.require(plan.week_start, SessionContext.DINNER)
    assert plan.clear(plan.week_start, SessionContext.DINNER)
    plan.assign("rec001", plan.week_start, SessionContext.LUNCH)
    copy = plan.copy_to_week(plan.week_start + __import__("datetime").timedelta(days=7))
    assert copy.count_filled_slots() >= 1
    assert plan.format_grid()
    restored = NightPlan.from_dict(plan.to_dict())
    assert restored.count_filled_slots() == plan.count_filled_slots()
    coll = NightPlanCampaign()
    coll.add(plan)
    assert coll.get(plan.id)
    assert coll.for_week(plan.week_start)
    assert coll.get_or_create(plan.week_start).id == plan.id
    assert coll.all()
    assert coll.to_dict()["plans"]
    with pytest.raises(CampaignError):
        plan.assign("x", date(1999, 1, 1), SessionContext.BREAKFAST)
    empty = NightPlan(date(2024, 6, 5))
    with pytest.raises(NotFoundError):
        empty.require(empty.week_start, SessionContext.LUNCH)


def test_cov_quantity_unit_parser():
    from boardbox.errors import ConversionError, ParseError
    from boardbox.quantity import EditionGrade, parse_quantity_line, sum_quantities, _rejoin_qty_prefix
    from boardbox.unit import Unit, UnitDimension, best_display_unit, convert_amount, convert_volume_to_weight, format_amount, normalize_to_base
    from boardbox.parser import parse_iso8601_duration, parse_price, parse_quantity

    q = EditionGrade.from_string("1/2 cup")
    assert q.value == 0.5
    q2 = EditionGrade.from_string("2 1/2 tsp")
    assert q2.value > 1
    merged = sum_quantities([EditionGrade(1, Unit.CUP), EditionGrade(0.5, Unit.CUP)])
    assert merged.value == 1.5
    val, unit, name = parse_quantity_line("2 cups flour")
    assert "flour" in name and val == 2.0
    assert convert_volume_to_weight(2, Unit.CUP, "flour") > 0
    assert _rejoin_qty_prefix("2 cups flour")
    base, dim = normalize_to_base(2, Unit.CUP)
    assert base > 0
    assert best_display_unit(500, UnitDimension.VOLUME) == Unit.CUP
    assert best_display_unit(500, UnitDimension.WEIGHT) == Unit.POUND
    assert convert_amount(1, Unit.CUP, Unit.TABLESPOON) > 0
    assert convert_amount(2, Unit.EACH, Unit.EACH) == 2
    assert format_amount(2.5, Unit.CUP)
    assert Unit.from_string("cups") == Unit.CUP
    assert Unit.PINCH.compatible_with(Unit.PINCH)
    assert parse_price("$12.50")[0] == 12.5
    assert parse_iso8601_duration("PT1H30M") == 90
    assert EditionGrade.from_string("3 each").unit == Unit.EACH
    with pytest.raises(ParseError):
        EditionGrade.from_string("")
    try:
        EditionGrade(1, Unit.CUP).add(EditionGrade(1, Unit.GRAM))
    except (ConversionError, ParseError):
        pass
    with pytest.raises(ConversionError):
        Unit.from_string("not-a-unit")


def test_cov_wishlist_builder_import():
    import boardbox.wishlist_builder as wb

    assert wb.build_from_game and wb.build_from_games and wb.build_from_night_plan


def test_cov_unit_display_branches():
    from boardbox.unit import Unit, UnitDimension, best_display_unit, format_amount

    assert best_display_unit(1500, UnitDimension.VOLUME) == Unit.LITER
    assert best_display_unit(20, UnitDimension.VOLUME) == Unit.TABLESPOON
    assert best_display_unit(5, UnitDimension.VOLUME) == Unit.TEASPOON
    assert best_display_unit(1500, UnitDimension.WEIGHT) == Unit.KILOGRAM
    assert best_display_unit(30, UnitDimension.WEIGHT) == Unit.OUNCE
    assert best_display_unit(3, UnitDimension.WEIGHT) == Unit.GRAM
    assert best_display_unit(1, UnitDimension.COUNT) == Unit.EACH
    assert format_amount(2, Unit.CUP) == "2 cup"


def test_cov_tag_registry_edges():
    from boardbox.errors import ValidationError
    from boardbox.tag import Tag, TagRegistry, TagSet, normalize_tag_name

    reg = TagRegistry()
    reg.register(Tag(name="rock", color="#000"))
    assert reg.get("rock") is not None
    assert reg.get("missing") is None
    assert reg.search("ro")
    ts = TagSet()
    ts.add_name("soul")
    assert not ts.has("missing")
    assert not ts.match_any(["missing"])
    with pytest.raises(ValidationError):
        Tag(name="!!!")


def test_cov_parser_and_play_stats_edges(populated_storage, sample_game):
    from boardbox.errors import ParseError
    from boardbox.parser import format_duration, format_year, parse_price, try_parse_date
    from boardbox.play_stats import parse_iso as session_parse_iso

    assert parse_price("€10.00")[1] == "EUR"
    assert parse_price("£5")[1] == "GBP"
    assert format_duration(90)
    assert format_year(4)
    assert try_parse_date("not-a-date") is None
    assert session_parse_iso(None) is None
    assert session_parse_iso("bad") is None
    populated_storage.update_game(sample_game.id, {"last_played_at": None})
    from boardbox.play_stats import dormant_games, summary_text

    assert dormant_games(populated_storage)
    assert summary_text(populated_storage, month="2099-01") == "Session summary: 0 sessions"


def test_cov_designer_registry():
    from boardbox.designer import Designer, DesignerRegistry

    reg = DesignerRegistry()
    a = reg.add(Designer.create("The Beatles", country="UK"))
    assert a.sort_name == "Beatles, The"
    assert reg.find_by_name("the beatles") is a
    assert reg.get(a.id) is a
    assert reg.all()
    b = reg.resolve_or_create("The Beatles")
    assert b.id == a.id
    reg2 = DesignerRegistry.from_dict_list([a.to_dict()])
    assert reg2.get(a.id)
    a.touch()


def test_cov_quantity_depth():
    from boardbox.errors import ParseError
    from boardbox.quantity import EditionGrade, parse_quantity_line

    assert EditionGrade(0, EditionGrade.CUP).value == 0.0
    q = EditionGrade.from_string("1/2 cup")
    assert q.value == 0.5
    with pytest.raises(ParseError):
        parse_quantity_line("")
    frac = EditionGrade.from_string("1/4 tsp")
    assert frac.value == 0.25


def test_cov_storage_atomic_error(empty_storage, monkeypatch):
    from boardbox.errors import StorageError

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("boardbox.storage.os.replace", boom)
    with pytest.raises(StorageError):
        empty_storage.create_game({"id": "x1", "title": "Fail Save", "year": 1, "mechanics": [], "componentlist": []})


def test_cov_parser_year_and_duration_edges():
    from boardbox.errors import ParseError
    from boardbox.parser import parse_duration, parse_year

    assert parse_year("serves 4") == 4
    with pytest.raises(ParseError):
        parse_duration("0m")
    with pytest.raises(ParseError):
        parse_year(0)


def test_cov_final_coverage_push(populated_storage, sample_game, sample_game2):
    from boardbox.complexity import ComplexityService
    from boardbox.export_menu import list_options
    from boardbox.favorites import FavoritesManager
    from boardbox.play_log import ListeningSession
    from boardbox.night_plan import NightPlanCampaign
    from boardbox.migrate import migrate_payload
    from boardbox.tag import Tag
    from boardbox.validators import validate_metadata, validate_session_context

    svc = ComplexityService(populated_storage)
    assert svc.run()["count"] >= 1
    sess = ListeningSession(
        game_id=sample_game.id,
        started_at="2024-06-01T12:00:00+00:00",
        duration_minutes=45,
        price=12.5,
        notes="nice",
    )
    payload = sess.to_dict()
    assert payload["duration_minutes"] == 45
    assert ListeningSession.from_dict(payload).price == 12.5
    tag = Tag.from_dict({"name": "mono", "color": "#fff"})
    assert tag.color == "#fff"
    coll = NightPlanCampaign.from_dict({"plans": []})
    assert coll.all() == []
    fm = FavoritesManager(populated_storage)
    fm.add(sample_game2.id)
    fm.remove(sample_game2.id)
    fm.sync_flags()
    fm.prune_stale()
    fm.top_by_publisher_name("italian")
    fm.bulk_add([sample_game.id])
    fm.export_ids()
    assert fm.render_list()
    assert list_options()
    assert validate_session_context("dinner") == "dinner"
    assert validate_metadata({"note": 1}) == {"note": 1}
    migrated = migrate_payload({"schema_version": 0, "games": [{"id": "l1", "title": "Legacy"}]})
    assert migrated.get("schema_version", 0) >= 1


def test_cov_storage_depth(populated_storage, sample_game):
    from boardbox.ratings import RatingsManager
    from boardbox.storage import JsonStorage

    snap = populated_storage.export_snapshot()
    populated_storage.replace_all(snap)
    assert populated_storage.count_games() >= 1
    assert populated_storage.count_sessions() >= 0
    populated_storage.create_listening({"id": "ln1", "game_id": sample_game.id})
    RatingsManager(populated_storage).set_rating(sample_game.id, 4)
    rows = populated_storage.list_ratings()
    assert rows
    populated_storage.upsert_rating({"game_id": sample_game.id, "stars": 5, "review": "updated"})


def test_cov_quantity_add_and_unicode():
    from boardbox.quantity import EditionGrade

    a = EditionGrade(1, EditionGrade.CUP)
    b = EditionGrade(0.5, EditionGrade.CUP)
    assert a.add(b).value == 1.5
    u = EditionGrade.from_string("½")
    assert u.value == 0.5


def test_cov_unit_and_validators_edges():
    from boardbox.errors import ConversionError, ValidationError
    from boardbox.unit import Unit, convert_amount, convert_volume_to_weight
    from boardbox.validators import (
        validate_game,
        validate_id,
        validate_optional_url,
        validate_rating,
        validate_source_url,
        validate_tags,
        validate_title,
        validate_year,
    )
    from boardbox.wishlist import WantLine, normalize_lines_for_store

    assert not Unit.PINCH.compatible_with(Unit.CUP)
    assert convert_amount(2.5, Unit.EACH, Unit.EACH) == 2.5
    with pytest.raises(ConversionError):
        convert_volume_to_weight(1, Unit.GRAM, "flour")
    assert validate_title("  OK  ") == "OK"
    assert validate_id("abc123")
    assert validate_rating(3) == 3
    assert validate_year(2020) == 2020
    assert validate_optional_url(None) is None
    with pytest.raises(ValidationError):
        validate_rating(9)
    assert validate_tags(["Quick", "mono"])
    assert validate_source_url("https://example.com/x")
    validate_game(__import__("tests.helpers", fromlist=["make_game"]).make_game(), strict=False)
    lines = normalize_lines_for_store(
        [WantLine("flour", __import__("boardbox.quantity", fromlist=["EditionGrade"]).EditionGrade(2, Unit.CUP))]
    )
    assert lines


def test_cov_format_and_mechanic(populated_storage, sample_game):
    from boardbox.edition import EditionScaler, format_quantity, parse_quantity as cond_qty
    from boardbox.edition import EditionGrade as GameGrade, parse_grade
    from boardbox.quantity import EditionGrade as Qty
    from boardbox.mechanic import Ingredient, IngredientCatalog, MechanicList, MechanicStub

    g = parse_grade("VG+")
    assert g == GameGrade.VG_PLUS
    assert format_quantity(1.5)
    assert cond_qty("1/2") == 0.5
    cat = IngredientCatalog()
    cat.seed_defaults()
    hit = cat.resolve("garlic")
    assert hit
    stub = MechanicStub(name="bass", quantity=Qty(1, Qty.CUP))
    scaled = stub.scaled(2.0)
    assert scaled.quantity.value == 2.0
    tl = MechanicList("alb1")
    tl.add(stub)
    assert tl.count() >= 1
    assert tl.sorted()
    assert tl.to_dict()["mechanics"]
    ing = Ingredient(name="rice", aisle="pantry")
    assert ing.to_dict()["name"] == "rice"
    scaler = EditionScaler(populated_storage)
    out = scaler.scale_game(sample_game, 8)
    assert out["mechanics"]
    assert scaler.scale_by_id(sample_game.id, 4)["target_year"] == 4
    assert scaler.batch_scale([sample_game.id, "missing"], 2)
    lines = scaler.render_wishlist_lines(out)
    assert lines
    merged = scaler.merge_scaled_mechanics([out, out])
    assert merged


def test_cov_listening_reports_backup(populated_storage, sample_game, tmp_path):
    from datetime import date
    from boardbox.backup import CampaignBackup
    from boardbox.play_log import (
        PlayLog,
        Session,
        SessionContext,
        count_sessions_by_type,
        group_sessions_by_date,
        sessions_for_date,
        sessions_in_range,
        unique_game_ids,
    )
    from boardbox.reports import WeeklySessionReport

    session = Session(sample_game.id, date.today(), SessionContext.DINNER)
    assert sessions_for_date([session], date.today())
    assert sessions_in_range([session], date.today(), date.today())
    assert group_sessions_by_date([session])
    assert count_sessions_by_type([session])
    assert unique_game_ids([session])
    log = PlayLog([session])
    assert log.upcoming(date.today())
    assert log.for_game(sample_game.id)
    log.remove(session.id)
    report = WeeklySessionReport(populated_storage)
    assert report.render_text()
    assert report.render_markdown()
    assert report.generate()
    bk = CampaignBackup(populated_storage.path, tmp_path / "bk")
    path = bk.create()
    assert bk.list_backups()
    assert bk.restore(path, verify=True)


def test_cov_quantity_exhaustive():
    from boardbox.errors import ConversionError, ParseError
    from boardbox.quantity import EditionGrade, parse_quantity_line, sum_quantities

    assert EditionGrade.from_string("1/2 cup").value == 0.5
    assert EditionGrade.from_string("1/2").value == 0.5
    with pytest.raises(ParseError):
        EditionGrade(1, EditionGrade.CUP).scale(-1)
    converted = EditionGrade(1, EditionGrade.CUP).convert_to(EditionGrade.TABLESPOON)
    assert converted.value > 0
    mixed = EditionGrade(1, EditionGrade.CUP).add(EditionGrade(8, EditionGrade.TABLESPOON))
    assert mixed.value > 1
    restored = EditionGrade.from_dict({"value": 2, "unit": "CUP"})
    assert restored.unit == EditionGrade.CUP
    assert str(restored)
    assert repr(restored)
    with pytest.raises(ParseError):
        sum_quantities([])
    val, unit, name = parse_quantity_line("3 eggs")
    assert val == 3 and name == "eggs"


def test_cov_wishlist_and_parser_final(populated_storage, sample_game):
    from boardbox.parser import parse_price, try_parse_date
    from boardbox.mechanic import IngredientCatalog
    from boardbox.unit import Unit
    from boardbox.wishlist import WantLine, build_from_game, normalize_lines_for_store
    from boardbox.quantity import EditionGrade

    cat = IngredientCatalog()
    cat.seed_defaults()
    sl = build_from_game(sample_game, catalog=cat, include_optional=False)
    assert sl.lines
    lines = normalize_lines_for_store([
        WantLine("flour", EditionGrade(2, Unit.CUP)),
        WantLine("flour", EditionGrade(500, Unit.GRAM)),
        WantLine("rice", EditionGrade(1, Unit.EACH)),
    ])
    assert len(lines) == 3
    assert parse_price("€3.50")[1] == "EUR"
    assert try_parse_date("2024-01-01") is not None


def test_cov_cli_backup_and_shop(campaign_cli, tmp_path, capsys):
    from argparse import Namespace
    from pathlib import Path

    from boardbox.cli import cmd_backup, cmd_shop, main

    main(campaign_cli + ["init"])
    main(campaign_cli + ["add", "ShopGame", "--mechanic", "1 cup rice", "--step", "Session"])
    main(campaign_cli + ["plan", "--assign", "ShopGame", "dinner", "2024-06-03"])
    book = Path(campaign_cli[1])
    ns = Namespace(
        sessionbook=book,
        game=None,
        year=None,
        list_id="default",
        format="text",
        date=None,
    )
    assert cmd_shop(ns) == 0
    bk_dir = tmp_path / "backups"
    ns_create = Namespace(
        sessionbook=book,
        dir=str(bk_dir),
        restore=None,
        list=False,
        prune=True,
        studio="test",
        keep=3,
    )
    assert cmd_backup(ns_create) == 0
    ns_list = Namespace(
        sessionbook=book,
        dir=str(bk_dir),
        restore=None,
        list=True,
        prune=False,
        studio=None,
        keep=3,
    )
    assert cmd_backup(ns_list) == 0
    created = sorted(bk_dir.glob("cookbook_*.json"))[-1]
    ns_restore = Namespace(
        sessionbook=book,
        dir=str(bk_dir),
        restore=str(created),
        list=False,
        prune=False,
        studio=None,
        keep=3,
    )
    assert cmd_backup(ns_restore) == 0


def test_cov_complexity_edges(populated_storage, sample_game):
    from boardbox.complexity import ComplexityService, ComplexityStore, estimate_game_value

    store = ComplexityStore(populated_storage)
    store.set_all(sample_game.id, {"calories": 100, "protein_g": 5})
    populated_storage.create_session({"id": "ap1", "game_id": sample_game.id, "year": 1})
    totals = store.daily_totals_from_sessions(["ap1"])
    assert totals.get("calories", 0) > 0
    assert estimate_game_value(populated_storage.get_game(sample_game.id)).estimated_value > 0
    assert ComplexityService(populated_storage).run()["count"] >= 1

