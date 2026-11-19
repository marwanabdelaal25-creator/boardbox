#!/usr/bin/env python3
"""Bootstrap boardbox from filmroll with board-game domain renames."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

SRC = Path(r"e:\AfterQuery\Silver\filmroll")
DST = Path(r"e:\AfterQuery\Silver\boardbox")

SKIP_DIRS = {
    ".git",
    ".history_snapshot",
    ".pytest_cache",
    "htmlcov",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
}
SKIP_FILES = {".coverage", "coverage_report.txt"}
KEEP_SCRIPTS = {
    "generate_covers.py",
    "generate_fixtures.py",
    "generate_imports.py",
    "package_zip.py",
    "verify_checklist.py",
    "_build_history.py",
    "_history_builder.py",
}

FILE_RENAMES = {
    "film.py": "game.py",
    "credit.py": "mechanic.py",
    "person.py": "designer.py",
    "studio.py": "publisher.py",
    "viewing_log.py": "play_log.py",
    "screening_stats.py": "play_stats.py",
    "format.py": "edition.py",
    "ticket.py": "order.py",
    "binder.py": "bin.py",
    "watchlist.py": "wishlist.py",
    "marathon.py": "campaign.py",
    "watch_plan.py": "night_plan.py",
    "scoring.py": "complexity.py",
    "io_letterboxd.py": "io_bgg.py",
    "io_imdb.py": "io_tabletop.py",
    "io_rt.py": "io_ludopoly.py",
}

HELPER_RENAMES = {
    "binders.py": "bins.py",
    "watchlist_list.py": "wishlist_list.py",
    "watchlist_builder.py": "wishlist_builder.py",
    "binder_tracker.py": "bin_tracker.py",
    "studio_name.py": "publisher_name.py",
}

REPLACEMENTS = [
    ("FILMROLL_HOME", "BOARDBOX_HOME"),
    ("filmroll", "boardbox"),
    ("Filmroll", "Boardbox"),
    ("FILMROLL", "BOARDBOX"),
    ("viewing_log", "play_log"),
    ("ViewingLog", "PlayLog"),
    ("screening_stats", "play_stats"),
    ("ScreeningStats", "PlayStats"),
    ("watch_plan", "night_plan"),
    ("WatchPlan", "NightPlan"),
    ("watchlist_list", "wishlist_list"),
    ("watchlist_builder", "wishlist_builder"),
    ("binder_tracker", "bin_tracker"),
    ("studio_name", "publisher_name"),
    ("watchlist", "wishlist"),
    ("Watchlist", "Wishlist"),
    ("io_letterboxd", "io_bgg"),
    ("io_imdb", "io_tabletop"),
    ("io_rt", "io_ludopoly"),
    ("Letterboxd", "Bgg"),
    ("letterboxd", "bgg"),
    ("Imdb", "Tabletop"),
    ("imdb", "tabletop"),
    ("WeeklyScreeningReport", "WeeklySessionReport"),
    ("ScreeningReport", "SessionReport"),
    ("last_screened_at", "last_played_at"),
    ("screened_at", "played_at"),
    ("list_screenings", "list_sessions"),
    ("create_screening", "create_session"),
    ("get_screening", "get_session"),
    ("delete_screening", "delete_session"),
    ("screenings", "sessions"),
    ("screening", "session"),
    ("Screening", "Session"),
    ("Scoring", "Complexity"),
    ("scoring", "complexity"),
    ("MarathonBackup", "CampaignBackup"),
    ("MarathonStats", "CampaignStats"),
    ("list_marathons", "list_campaigns"),
    ("create_marathon", "create_campaign"),
    ("marathon.json", "library.json"),
    ("marathon_path", "library_path"),
    ("marathon", "campaign"),
    ("Marathon", "Campaign"),
    ("BinderTracker", "BinTracker"),
    ("list_binders", "list_bins"),
    ("create_binder", "create_bin"),
    ("update_binder", "update_bin"),
    ("delete_binder", "delete_bin"),
    ("binders", "bins"),
    ("binder", "bin"),
    ("Binder", "Bin"),
    ("FilmSearch", "GameSearch"),
    ("FilmIndex", "GameIndex"),
    ("list_films", "list_games"),
    ("get_film", "get_game"),
    ("create_film", "create_game"),
    ("update_film", "update_game"),
    ("delete_film", "delete_game"),
    ("film_id", "game_id"),
    ("films", "games"),
    ("Film", "Game"),
    ("film", "game"),
    ("CreditStub", "MechanicStub"),
    ("castlist", "componentlist"),
    ("credits", "mechanics"),
    ("Credit", "Mechanic"),
    ("credit", "mechanic"),
    ("Person", "Designer"),
    ("person", "designer"),
    ("Studio", "Publisher"),
    ("Publisher", "Publisher"),
    ("FormatScaler", "EditionScaler"),
    ("FormatGrade", "EditionGrade"),
    ("Format", "Edition"),
    ("Ticket", "Order"),
    ("ticket", "order"),
    ("movie", "title"),
    ("movies", "titles"),
    ("director", "designer_name"),
    ("Letterboxd", "BoardGameGeek"),
    ("watch diary", "game library"),
    ("watchlist", "wishlist"),
]

ORPHAN_MODULES = {
    "quantity.py",
    "unit.py",
    "scale.py",
    "meal.py",
    "nutrition.py",
    "timer.py",
    "bins.py",
    "collections.py",
    "wishlist_list.py",
    "wishlist_builder.py",
    "bin_tracker.py",
    "publisher_name.py",
}


def should_skip(rel: Path) -> bool:
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts):
        return True
    if rel.name in SKIP_FILES:
        return True
    if parts[0] == "scripts" and rel.name.endswith(".py"):
        if rel.name in KEEP_SCRIPTS:
            return False
        if rel.name.startswith("_") and rel.name not in KEEP_SCRIPTS:
            return True
    if parts[0] == "tests" and len(parts) > 1 and parts[1] == "fixtures":
        return True
    return False


def port_text(text: str) -> str:
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def copy_tree() -> None:
    if DST.exists():
        shutil.rmtree(DST)
    for root, dirs, files in SRC.walk():
        rel_root = root.relative_to(SRC)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for fname in files:
            rel = rel_root / fname
            if should_skip(rel):
                continue
            src_file = root / fname
            dst_file = DST / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            if fname.endswith((".py", ".md", ".toml", ".ini", ".yml", ".yaml")) or fname in {
                "Makefile",
                "LICENSE",
                "Dockerfile",
            }:
                dst_file.write_text(port_text(src_file.read_text(encoding="utf-8", errors="ignore")), encoding="utf-8")
            else:
                shutil.copy2(src_file, dst_file)


def rename_package() -> None:
    old_pkg = DST / "src" / "filmroll"
    new_pkg = DST / "src" / "boardbox"
    if old_pkg.exists():
        old_pkg.rename(new_pkg)
    for old, new in FILE_RENAMES.items():
        for base in (new_pkg, DST / "tests"):
            p = base / old
            if p.exists():
                p.rename(base / new)
    for mod in ORPHAN_MODULES:
        p = new_pkg / mod
        if p.exists():
            p.unlink()


def rename_tests() -> None:
    tests = DST / "tests"
    for old, new in FILE_RENAMES.items():
        src = tests / f"test_{old.replace('.py', '')}.py"
        dst = tests / f"test_{new.replace('.py', '')}.py"
        if src.exists():
            src.rename(dst)


def restore_helpers() -> None:
    src_pkg = SRC / "src" / "filmroll"
    dst_pkg = DST / "src" / "boardbox"
    keep = {
        "quantity.py",
        "unit.py",
        "scale.py",
        "meal.py",
        "nutrition.py",
        "timer.py",
        "collections.py",
    }
    for name in keep:
        text = port_text((src_pkg / name).read_text(encoding="utf-8"))
        (dst_pkg / name).write_text(text, encoding="utf-8")
    for old, new in HELPER_RENAMES.items():
        text = port_text((src_pkg / old).read_text(encoding="utf-8"))
        (dst_pkg / new).write_text(text, encoding="utf-8")


def fix_collections_stdlib() -> None:
    pkg = DST / "src" / "boardbox"
    for py in pkg.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        fixed = text.replace("from campaigns import", "from collections import")
        fixed = fixed.replace("import campaigns.", "import collections.")
        if fixed != text:
            py.write_text(fixed, encoding="utf-8")


def fix_cross_imports() -> None:
    pkg = DST / "src" / "boardbox"
    subs = [
        ("from .binders import", "from .bins import"),
        ("from .binder_tracker import", "from .bin_tracker import"),
        ("from .studio_name import", "from .publisher_name import"),
        ("from .watchlist_list import", "from .wishlist_list import"),
        ("from .watchlist_builder import", "from .wishlist_builder import"),
    ]
    for py in pkg.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        for old, new in subs:
            text = text.replace(old, new)
        if "copyard" in text:
            text = text.replace("copyard", "discard")
        py.write_text(text, encoding="utf-8")

    for py in (DST / "tests").glob("*.py"):
        text = py.read_text(encoding="utf-8")
        text = text.replace("boardbox.binders", "boardbox.bins")
        text = text.replace("boardbox.studio_name", "boardbox.publisher_name")
        text = text.replace("boardbox.binder_tracker", "boardbox.bin_tracker")
        text = text.replace("filmroll.", "boardbox.")
        text = text.replace("from boardbox.campaigns import", "from boardbox.collections import")
        text = text.replace("boardbox.campaigns import", "boardbox.collections import")
        py.write_text(text, encoding="utf-8")

    # test_marathon -> test_campaign imports
    tc = DST / "tests" / "test_campaign.py"
    if tc.exists():
        t = tc.read_text(encoding="utf-8")
        t = t.replace("boardbox.campaigns", "boardbox.collections")
        t = t.replace('"""Tests for boardbox.campaigns."""', '"""Tests for boardbox.collections."""')
        tc.write_text(t, encoding="utf-8")


def patch_configs() -> None:
    pyproject = DST / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(
        r'name = "filmroll"',
        'name = "boardbox"',
        text,
    )
    text = text.replace("filmroll", "boardbox")
    text = re.sub(
        r'description = ".*?"',
        'description = "A personal board game library CLI — BGG is fine until you want offline grep"',
        text,
    )
    text = re.sub(
        r'keywords = \[.*?\]',
        'keywords = ["cli", "board-games", "bgg", "tabletop", "wishlist"]',
        text,
        flags=re.DOTALL,
    )
    pyproject.write_text(text, encoding="utf-8")

    mods = '''SOURCE_MODULES = {
    "errors", "parser", "validators", "game", "mechanic", "designer", "publisher",
    "tag", "edition", "order", "play_log", "wishlist", "bin", "shelf",
    "storage", "migrate", "backup", "search", "stats", "play_stats", "reports",
    "reminders", "recurring", "seasonal", "ratings", "favorites", "archive",
    "campaign", "night_plan", "tags_manager", "notes", "audit_log", "plugins", "import_merge",
    "export_menu", "server", "io_csv", "io_jsonl", "io_bgg", "io_tabletop",
    "io_ludopoly", "complexity", "cli",
}'''
    for script in ("package_zip.py", "verify_checklist.py", "_build_history.py"):
        p = DST / "scripts" / script
        t = port_text(p.read_text(encoding="utf-8"))
        t = t.replace('PROJECT = "boardbox"', 'PROJECT = "boardbox"')
        if script == "verify_checklist.py":
            t = re.sub(r"SOURCE_MODULES = \{[^}]+\}", mods, t, flags=re.DOTALL)
            t = t.replace("filmroll Silver", "boardbox Silver")
        if script == "_build_history.py":
            t = t.replace(".filmroll_history_backup", ".boardbox_history_backup")
        p.write_text(t, encoding="utf-8")

    readme = DST / "README.md"
    readme.write_text(
        """# boardbox

Personal board game library CLI I wrote because BoardGameGeek is great for
community stuff but I wanted something grep-friendly on disk.

One JSON file (`library.json` by default), no cloud sync, no accounts.
Import a CSV export from BGG when I feel like it, then grep my collection
from the terminal.

## What it does

- Track owned games (base, expansions, promos) with edition notes
- Log play sessions with date, player count, venue, notes
- Wishlist + order ledger for Kickstarter/backorder tracking
- Campaign plans (e.g. "Gloomhaven saga", "Wingspan family night")
- Tags, ratings, favorites, seasonal filters
- Search across title, designer, publisher, mechanics
- Weekly play stats and simple text reports
- Import adapters: BGG collection CSV, Tabletop Library export, Ludopoly dump
- Tiny stdlib HTTP server to browse the shelf on LAN

## What it doesn't do

- No live BGG API lookups — I type titles myself
- No box art hosting — local PNG paths only
- No multi-user anything — one person's shelf

## Quick start

```bash
pip install .
boardbox init ~/games/library.json
boardbox add --title "Wingspan" --year 2019 --designer "Elizabeth Hargrave"
boardbox session game001 --date 2024-03-12 --players 3
boardbox list --tag engine-builder
boardbox stats --month
```

## Author

Marwan Helmy — marwanabdelaal25@gmail.com

MIT license. Side project, Sep 2024–present.
""",
        encoding="utf-8",
    )


def main() -> None:
    print("Copying filmroll -> boardbox ...")
    copy_tree()
    rename_package()
    rename_tests()
    restore_helpers()
    fix_collections_stdlib()
    fix_cross_imports()
    patch_configs()
    print("Done:", DST)


if __name__ == "__main__":
    main()
