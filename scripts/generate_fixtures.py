#!/usr/bin/env python3
"""Generate large board game library JSON fixtures (stdlib only)."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "libraries"

TITLES = [
    "Wingspan", "Terraforming Mars", "Azul", "Catan", "Ticket to Ride",
    "Gloomhaven", "Spirit Island", "Root", "Brass: Birmingham", "Pandemic",
    "Everdell", "Scythe", "Ark Nova", "Dune: Imperium", "Cascadia",
]
PERSONAS = [
    "euro_collector", "ameritrash_shelf", "solo_gamer", "family_night",
    "kickstarter_backer", "miniatures_crate", "party_games_bin", "legacy_runner",
    "two_player_only", "filler_shelf",
]
DESIGNERS = ["Hargrave", "Feld", "Kiesling", "Teuber", "Moon", "Lehman", "O'Malley"]
MECHANICS = ["engine-builder", "worker-placement", "deck-building", "area-control", "co-op"]


def _game(rng: random.Random, idx: int) -> dict:
    n_mech = rng.randint(3, 8)
    mechanics = [
        {
            "title": rng.choice(MECHANICS),
            "mechanic_number": str(s + 1),
            "role": rng.choice(["core", "secondary", "variant"]),
        }
        for s in range(n_mech)
    ]
    return {
        "id": f"game-{idx:06d}",
        "title": f"{rng.choice(TITLES)} #{idx}",
        "designer_ids": [f"des-{rng.randint(1, 40):03d}"],
        "year": rng.randint(1995, 2025),
        "playtime_min": rng.randint(20, 180),
        "player_count": f"{rng.randint(1,4)}-{rng.randint(4,6)}",
        "mechanics": mechanics,
        "edition": rng.choice(["retail", "kickstarter", "deluxe", "second_edition"]),
        "box_edition": rng.choice(["mint", "good", "shelf_wear"]),
        "session_count": rng.randint(0, 40),
        "tag_ids": [f"tag-{rng.randint(1, 20)}" for _ in range(rng.randint(0, 3))],
        "release": {"sku": f"SKU-{idx:05d}", "country": rng.choice(["US", "DE", "UK", "CN"])},
    }


def _library(rng: random.Random, name: str, n_games: int) -> dict:
    games = [_game(rng, i) for i in range(n_games)]
    return {
        "schema_version": 2,
        "meta": {"name": name, "persona": rng.choice(PERSONAS)},
        "games": games,
        "sessions": [],
        "wishlist": [],
        "tags": [],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20260608)
    specs = [
        ("megashelf-1", 880),
        ("megashelf-2", 1020),
        ("megashelf-3", 790),
        ("persona-euro_collector", 120),
        ("persona-ameritrash_shelf", 95),
        ("persona-solo_gamer", 80),
        ("persona-family_night", 110),
        ("persona-kickstarter_backer", 90),
        ("persona-miniatures_crate", 85),
        ("persona-party_games_bin", 100),
        ("persona-legacy_runner", 88),
        ("persona-two_player_only", 75),
        ("persona-filler_shelf", 82),
    ]
    for year in range(2019, 2026):
        specs.append((f"snapshot-{year}", rng.randint(40, 70)))

    total_bytes = 0
    for fname, count in specs:
        data = _library(rng, fname, count)
        path = OUT / f"{fname}.json"
        text = json.dumps(data, indent=2)
        path.write_text(text, encoding="utf-8")
        total_bytes += len(text.encode())
    print(f"wrote {len(specs)} library fixtures ({total_bytes / (1024*1024):.2f} MB raw)")


if __name__ == "__main__":
    main()
