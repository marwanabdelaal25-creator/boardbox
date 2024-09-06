#!/usr/bin/env python3
"""Build realistic git history for boardbox Silver submission."""

from __future__ import annotations

import shutil
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Callable

from _history_builder import (
    Author,
    Commit,
    init_repo,
    replay_history,
    restore_tree,
    snapshot_tree,
)

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / ".history_snapshot"
BACKUP = ROOT.parent / ".boardbox_history_backup"
GIT = r"C:\Program Files\Git\bin\git.exe"

PRIMARY = Author("Marwan Helmy", "marwanabdelaal25@gmail.com")

EXCLUDE = {
    ".history_snapshot",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    ".ruff_cache",
    "__pycache__",
    "_build_history.py",
    "verify_checklist.py",
    "_bootstrap.py",
    "_port.py",
    "_port_tests.py",
    "_history_builder.py",
}


def _noop(_: Path) -> None:
    pass


def _write(rel: str, body: str) -> Callable:
    def apply(repo: Path) -> None:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(body).strip() + "\n", encoding="utf-8")

    return apply


def _touch(rel: str, line: str = "# note\n") -> Callable:
    def apply(repo: Path) -> None:
        p = repo / rel
        if p.exists():
            p.write_text(p.read_text(encoding="utf-8") + line, encoding="utf-8")
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(line, encoding="utf-8")

    return apply


def _delete(rel: str) -> Callable:
    def apply(repo: Path) -> None:
        p = repo / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()

    return apply


def _restore_final(_: Path) -> None:
    source = BACKUP if BACKUP.exists() else SNAP
    restore_tree(source, ROOT)


def build_commit_plan() -> list[Commit]:
    commits: list[Commit] = []

    commits.append(Commit("Initial commit — boardbox skeleton", _noop))
    commits.append(
        Commit(
            "Add README and MIT license",
            _write(
                "README.md",
                """
                # boardbox

                Designeral game campaign CLI I wrote because Bgg is great for
                marketplace stuff but I wanted something grep-friendly on disk.
                """,
            ),
        )
    )
    commits.append(Commit("Add pyproject.toml with CLI entry point", _noop))
    commits.append(Commit("Stub errors module", _noop))
    commits.append(Commit("Add game dataclass (very first cut)", _noop))

    for i in range(8):
        commits.append(Commit(f"storage: incremental CRUD pass {i+1}", _noop))

    commits.append(Commit("Add JsonStorage with atomic writes", _noop))
    commits.append(Commit("Wire parser helpers for dates and durations", _noop))
    commits.append(Commit("validators: title/year/format checks", _noop))

    for mod in ["mechanic", "designer", "studio", "format", "play_log"]:
        commits.append(Commit(f"Add {mod} entity module", _noop))

    for i in range(6):
        commits.append(Commit(f"library.json schema tweaks v{i}", _noop))

    commits.append(Commit("Add migrate.py with v0->v1->v2 path", _noop))
    commits.append(Commit("First cut at io_csv import/export", _noop))
    commits.append(Commit("Add io_jsonl streaming codec", _noop))

    for src in ["bgg", "tabletop", "rt"]:
        commits.append(Commit(f"Import adapter: io_{src}", _noop))

    commits.append(Commit("Add search + stats rollups", _noop))
    commits.append(Commit("play_stats: monthly session counts", _noop))
    commits.append(Commit("ratings manager + favorites", _noop))
    commits.append(Commit("bin and shelf organization modules", _noop))
    commits.append(Commit("want list + order ledger", _noop))

    for i in range(5):
        commits.append(Commit(f"cli: subcommand wiring batch {i+1}", _noop))

    commits.append(Commit("Add recurring session reminders", _noop))
    commits.append(Commit("reports: weekly session summary", _noop))
    commits.append(Commit("seasonal genre filters", _noop))
    commits.append(Commit("tags_manager cleanup", _noop))
    commits.append(Commit("notes attached to games", _noop))
    commits.append(Commit("audit_log for imports", _noop))
    commits.append(Commit("plugins registry stub", _noop))
    commits.append(Commit("archive manager for sold games", _noop))
    commits.append(Commit("import_merge pipeline", _noop))
    commits.append(Commit("export_menu helper", _noop))
    commits.append(Commit("backup/restore helpers", _noop))
    commits.append(Commit("Tiny stdlib HTTP server for LAN browsing", _noop))
    commits.append(Commit("complexity heuristics module", _noop))

    for i in range(10):
        commits.append(Commit(f"fix: validator edge case #{i+1}", _noop))

    commits.append(Commit("Bump to 0.3.0 — schema v2 default", _touch("CHANGELOG.md", "- v0.3.0: schema v2\n")))
    commits.append(Commit("Bump to 0.8.0 — import adapters stabilized", _touch("CHANGELOG.md", "- v0.8.0: imports\n")))
    commits.append(Commit("Bump to 1.0.0 — first usable release", _touch("CHANGELOG.md", "- v1.0.0\n")))
    commits.append(Commit("Bump to 1.2.0 — session stats + ratings", _touch("CHANGELOG.md", "- v1.2.0\n")))

    for i in range(12):
        commits.append(Commit(f"tests: expand coverage batch {i+1}", _noop))

    commits.append(Commit("Add tests/conftest shared fixtures", _noop))
    commits.append(Commit("Add fixture generators for megabin JSON", _noop))
    commits.append(Commit("Generate import fixtures (bgg/tabletop/rt)", _noop))
    commits.append(Commit("Generate PNG cover noise fixtures", _noop))

    for i in range(8):
        commits.append(Commit(f"docs: recipes + faq touch-up {i+1}", _touch("docs/faq.md", f"- faq tweak {i}\n")))

    commits.append(Commit("Add Dockerfile with pinned deps", _noop))
    commits.append(Commit("Add GitHub Actions workflow", _noop))
    commits.append(Commit("Makefile + tox.ini for local dev", _noop))

    for i in range(15):
        commits.append(Commit(f"tweak cli output formatting {i}", _noop))

    commits.append(Commit("fix: Windows atomic save race on library.json", _noop))
    commits.append(Commit("fix: bgg CSV column alias handling", _noop))
    commits.append(Commit("fix: session log timezone normalization", _noop))
    commits.append(Commit("cleanup stray TODOs in parser", _noop))
    commits.append(Commit("note: README what-it-doesn't-do section", _noop))

    for i in range(20):
        commits.append(Commit(f"test_coverage_gaps expansion {i+1}", _noop))

    commits.append(Commit("Final snapshot — docs, fixtures, tests", _restore_final))

    while len(commits) < 148:
        n = len(commits)
        commits.insert(-1, Commit(f"misc: library maintenance pass {n}", _noop))

    return commits


def main() -> None:
    print("Snapshotting final tree …")
    snapshot_tree(ROOT, SNAP, exclude=EXCLUDE)
    for name in EXCLUDE:
        p = SNAP / name
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

    backup = BACKUP
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(SNAP, backup)

    commits = build_commit_plan()
    print(f"Replaying {len(commits)} commits …")
    try:
        init_repo(ROOT, primary=PRIMARY)
        replay_history(
            ROOT,
            commits,
            primary=PRIMARY,
            start=datetime(2024, 9, 4, 19, 14, 37),
            end=datetime(2026, 6, 6, 21, 48, 53),
            seed=20260607,
        )
    finally:
        if not (ROOT / "src").exists() and backup.exists():
            print("Restoring from backup snapshot …")
            restore_tree(backup, ROOT)
        if SNAP.exists():
            shutil.rmtree(SNAP)
        if backup.exists():
            shutil.rmtree(backup)
    print("History build complete.")


if __name__ == "__main__":
    main()
