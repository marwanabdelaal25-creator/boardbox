#!/usr/bin/env python3
"""Typical workflow: import Bgg CSV and print session stats."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from boardbox.io_bgg import import_bgg_csv
from boardbox.play_log import log_session
from boardbox.play_stats import sessions_by_month
from boardbox.storage import JsonStorage


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory() as td:
        store = JsonStorage(Path(td) / "game.json")
        if csv_path and csv_path.exists():
            rows = import_bgg_csv(csv_path.read_text(encoding="utf-8"))
            for row in rows:
                store.create_game(row)
            print("imported %d games" % len(rows))
        else:
            store.create_game({"title": "Demo Game", "designer_name": "Demo Director", "year": 1984})
        alb = store.list_games()[0]
        log_session(store, game_id=alb["id"], note="example session")
        print(sessions_by_month(store))


if __name__ == "__main__":
    main()
