"""Shared pytest fixtures for boardbox tests."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from boardbox.game import Game
from boardbox.storage import JsonStorage

from tests.helpers import make_game, make_campaign_dict, make_bin_item, make_mechanic_line


@pytest.fixture
def tmp_library_path(tmp_path: Path) -> Path:
    return tmp_path / "library.json"


@pytest.fixture
def empty_storage(tmp_library_path: Path) -> JsonStorage:
    return JsonStorage(tmp_library_path)


@pytest.fixture
def sample_game() -> Game:
    return make_game(
        "Sunday Pasta",
        game_id="rec001",
        publisher_name="italian",
        format="main",
        tag_ids=["jazz", "quick"],
    )


@pytest.fixture
def sample_game2() -> Game:
    return make_game(
        "Garden Salad",
        game_id="rec002",
        publisher_name="american",
        format="salad",
        year=2,
        mechanics=[make_mechanic_line("lettuce", quantity=1.0, unit="head")],
    )


@pytest.fixture
def sample_night_plan() -> dict:
    return make_campaign_dict()


@pytest.fixture
def populated_storage(
    empty_storage: JsonStorage,
    sample_game: Game,
    sample_game2: Game,
    sample_night_plan: dict,
) -> JsonStorage:
    empty_storage.create_game(sample_game)
    empty_storage.create_game(sample_game2)
    empty_storage.create_campaign(sample_night_plan)
    empty_storage.create_bin(make_bin_item())
    empty_storage.create_bin(
        make_bin_item("butter", item_id="pan002", quantity=1.0, unit="lb")
    )
    empty_storage.create_tag({"id": "quick", "name": "quick"})
    empty_storage.create_tag({"id": "vegetarian", "name": "vegetarian"})
    empty_storage.create_note(
        {
            "id": "note001",
            "game_id": sample_game.id,
            "body": "Family favorite",
        }
    )
    empty_storage.create_want(
        {
            "id": "shop001",
            "list_id": "weekly",
            "name": "pasta",
            "quantity": 2,
            "unit": "lb",
            "checked": False,
        }
    )
    empty_storage.add_favorite(sample_game.id)
    empty_storage.create_campaign(
        {
            "id": "col001",
            "name": "Weeknight",
            "game_ids": [sample_game.id, sample_game2.id],
        }
    )
    return empty_storage


@pytest.fixture
def sample_games_csv() -> str:
    return (
        "title,year,publisher_name,format,mechanics,componentlist,source_url,tags\n"
        "Imported Soup,6,american,soup,"
        '"tomato ;; 2 can ;; ;;\n onion ;; 1 each ;; ;;",'
        '"1. Chop ;; 2. Simmer",,comfort\n'
        "Quick Toast,2,,breakfast,"
        '"bread ;; 2 slice ;; ;;",'
        '"1. Toast",,\n'
    )


@pytest.fixture
def sample_wishlist_csv() -> str:
    return "name,quantity,unit,aisle,checked\nmilk,1,gallon,dairy,false\n"


@pytest.fixture
def sample_jsonl_games() -> str:
    lines = [
        {
            "_type": "game",
            "id": "jl001",
            "title": "JSONL Curry",
            "year": 4,
            "mechanics": [{"name": "rice", "quantity": 2.0, "unit": "cup"}],
            "componentlist": [{"order": 1, "text": "Session rice"}],
        },
        {
            "_type": "game",
            "id": "jl002",
            "title": "JSONL Salad",
            "year": 2,
            "mechanics": [],
            "componentlist": [{"order": 1, "text": "Toss"}],
        },
    ]
    return "\n".join(json.dumps(row) for row in lines) + "\n"


@pytest.fixture
def sample_bgg_json() -> str:
    payload = {
        "games": [
            {
                "name": "Bgg Stew",
                "year": 4,
                "mechanics": ["2 cups broth", "1 onion"],
                "directions": ["Simmer", "Serve"],
                "categories": ["comfort"],
                "source": "https://example.com/stew",
            }
        ]
    }
    return json.dumps(payload)


@pytest.fixture
def sample_tabletop_csv() -> str:
    return (
        "Game Name,Ingredients,Instructions,Servings\n"
        "Tabletop Bowl,rice|tofu,1. Session rice. 2. Top.,2\n"
    )


@pytest.fixture
def sample_sessionmate_csv() -> str:
    return (
        "Title,Ingredient,Amount,Unit,Step,Servings\n"
        "Rt Pie,apples,4,each,Peel apples,8\n"
        "Rt Pie,sugar,1,cup,Peel apples,8\n"
        "Rt Pie,,,,Bake 45m,8\n"
    )


@pytest.fixture
def v0_campaign_list() -> list:
    return [
        {
            "id": "legacy1",
            "title": "Legacy Soup",
            "mechanics": ["1 cup broth"],
            "componentlist": ["Heat"],
        }
    ]


@pytest.fixture
def v1_campaign_dict() -> dict:
    return {
        "schema_version": 1,
        "games": [
            {
                "id": "v1r1",
                "title": "V1 Dish",
                "tags": ["old-tag"],
                "mechanics": ["salt"],
            }
        ],
    }


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
