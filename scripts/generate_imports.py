#!/usr/bin/env python3
"""Generate multi-source game import fixtures (stdlib only)."""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "imports"

SOURCES = [
    "bgg", "tabletop", "ludopoly", "csv_native", "jsonl_events",
    "gamestore", "wishlist", "kickstarter", "pnp", "convention",
]


def _rng(source: str, year: int, month: int) -> random.Random:
    return random.Random(hash((source, year, month)) & 0xFFFFFFFF)


def _write_bgg(path: Path, rng: random.Random, n: int) -> None:
    releases = []
    for i in range(n):
        releases.append({
            "release_id": f"dg-{i:06d}",
            "title": f"Release {i}",
            "designer": rng.choice(["Hargrave", "Teuber", "Feld"]),
            "year": str(rng.randint(1995, 2024)),
            "edition": rng.choice(["retail", "kickstarter", "deluxe"]),
            "mechanics": rng.choice(["Engine Builder", "Worker Placement", "Drafting"]),
            "componentlist": ["Main board", "Rulebook", "Meeples"],
        })
    path.write_text(json.dumps({"releases": releases}, indent=2), encoding="utf-8")


def _write_tabletop(path: Path, rng: random.Random, n: int) -> None:
    fields = ["Release Title", "Designer", "Year", "Edition", "Publisher"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(n):
            w.writerow({
                "Release Title": f"MB Game {i}",
                "Designer": rng.choice(["Coltrane", "Davis"]),
                "Year": str(rng.choice([1959, 1965, 1973])),
                "Edition": "LP",
                "Publisher": "Blue Note",
            })


def _write_rt(path: Path, rng: random.Random, n: int) -> None:
    fields = ["game", "designer", "mechanic", "duration_ms"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(n):
            w.writerow({
                "game": f"Rt LP {i // 3}",
                "designer": rng.choice(["Radiohead", "Beatles"]),
                "mechanic": f"Mechanic {i % 8}",
                "duration_ms": str(rng.randint(120000, 360000)),
            })


def _write_native(path: Path, rng: random.Random, n: int) -> None:
    fields = ["title", "year", "format", "genres", "catalog_number", "mechanics"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(n):
            w.writerow({
                "title": f"Native {i}",
                "year": "1970",
                "format": "LP",
                "genres": "jazz",
                "catalog_number": f"N-{i:04d}",
                "mechanics": "A1 Opener|B1 Closer",
            })


def _write_jsonl(path: Path, rng: random.Random, n: int) -> None:
    lines = []
    for i in range(n):
        lines.append(json.dumps({
            "_type": "game",
            "id": f"imp-{i:05d}",
            "title": f"Import {i}",
            "year": rng.randint(1960, 2020),
        }))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


WRITERS = {
    "bgg": lambda p, r, n: _write_bgg(p.with_suffix(".json"), r, n),
    "tabletop": lambda p, r, n: _write_tabletop(p.with_suffix(".csv"), r, n),
    "rt": lambda p, r, n: _write_rt(p.with_suffix(".csv"), r, n),
    "csv_native": lambda p, r, n: _write_native(p.with_suffix(".csv"), r, n),
    "jsonl_events": lambda p, r, n: _write_jsonl(p.with_suffix(".jsonl"), r, n),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in SOURCES:
        src_dir = OUT / source
        src_dir.mkdir(parents=True, exist_ok=True)
        for year in range(2019, 2026):
            year_dir = src_dir / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            for month in range(1, 13):
                rng = _rng(source, year, month)
                n = rng.randint(3, 12)
                base = year_dir / f"{source}_{year}_{month:02d}"
                writer = WRITERS.get(source, WRITERS["csv_native"])
                writer(base, rng, n)
                for p in year_dir.glob(f"{source}_{year}_{month:02d}.*"):
                    total += p.stat().st_size
    print(f"wrote import fixtures ({total / (1024*1024):.2f} MB raw)")


if __name__ == "__main__":
    main()
