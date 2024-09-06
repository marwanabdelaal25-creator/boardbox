#!/usr/bin/env python3
"""Monthly session summary report."""

from __future__ import annotations

import sys
from pathlib import Path

from boardbox.reports import session_report_text
from boardbox.storage import JsonStorage


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("game.json")
    month = sys.argv[2] if len(sys.argv) > 2 else None
    store = JsonStorage(path)
    text = session_report_text(store, month=month)
    print(text)


if __name__ == "__main__":
    main()
