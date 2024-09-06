#!/usr/bin/env python3
"""Build want list from Rt export minus existing campaign."""

from __future__ import annotations

import sys
from pathlib import Path

from boardbox.io_ludopoly import rt_missing_from_campaign
from boardbox.storage import JsonStorage


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: want_from_rt.py library.json rt_export.csv")
        raise SystemExit(1)
    store = JsonStorage(Path(sys.argv[1]))
    csv_text = Path(sys.argv[2]).read_text(encoding="utf-8")
    missing = rt_missing_from_campaign(store, csv_text)
    for item in missing[:20]:
        print("%s — %s" % (item.get("designer"), item.get("title")))
    print("... %d total candidates" % len(missing))


if __name__ == "__main__":
    main()
