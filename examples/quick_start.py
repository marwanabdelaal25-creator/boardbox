#!/usr/bin/env python3
"""Smoke test — init and add one game."""

from __future__ import annotations

import tempfile
from pathlib import Path

from boardbox.game import Game
from boardbox.storage import JsonStorage


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "game.json"
        store = JsonStorage(path)
        alb = Game(title="Past Lives", designer_name="Celine Song", year=2023, format="streaming")
        created = store.create_game(alb.to_dict())
        print("created game", created["id"], created["title"])
        assert store.get_game(created["id"]) is not None
        print("ok")


if __name__ == "__main__":
    main()
