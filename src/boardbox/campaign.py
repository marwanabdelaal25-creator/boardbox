"""Game groupings / campaigns (e.g. weeknight dinners).

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from typing import Iterable, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


class CampaignManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def create(
        self,
        name: str,
        description: str = "",
        game_ids: Optional[Iterable[str]] = None,
    ) -> dict:
        if not name.strip():
            raise ValidationError("campaign name required")
        ids = list(game_ids or [])
        for rid in ids:
            self.storage.get_game(rid)
        return self.storage.create_campaign({
            "id": uuid.uuid4().hex[:12],
            "name": name.strip(),
            "description": description,
            "game_ids": ids,
        })

    def list_all(self) -> list[dict]:
        return self.storage.list_campaigns()

    def get(self, campaign_id: str) -> dict:
        for c in self.list_all():
            if c.get("id") == campaign_id:
                return c
        raise NotFoundError("campaigns", campaign_id)

    def add_game(self, campaign_id: str, game_id: str) -> dict:
        coll = self.get(campaign_id)
        self.storage.get_game(game_id)
        ids = list(coll.get("game_ids", []))
        if game_id not in ids:
            ids.append(game_id)
        return self.storage.update_campaign(campaign_id, {"game_ids": ids})

    def remove_game(self, campaign_id: str, game_id: str) -> dict:
        coll = self.get(campaign_id)
        ids = [x for x in coll.get("game_ids", []) if x != game_id]
        return self.storage.update_campaign(campaign_id, {"game_ids": ids})

    def rename(self, campaign_id: str, name: str) -> dict:
        if not name.strip():
            raise ValidationError("name required")
        return self.storage.update_campaign(campaign_id, {"name": name.strip()})

    def delete(self, campaign_id: str) -> None:
        self.storage.delete_campaign(campaign_id)

    def games_in(self, campaign_id: str) -> list[dict]:
        coll = self.get(campaign_id)
        out = []
        for rid in coll.get("game_ids", []):
            try:
                out.append(self.storage.get_game(rid).to_dict())
            except NotFoundError:
                pass  # stale id — TODO cleanup helper
        return out

    def campaigns_for_game(self, game_id: str) -> list[dict]:
        return [
            c for c in self.list_all()
            if game_id in c.get("game_ids", [])
        ]

    def merge(self, target_id: str, source_id: str) -> dict:
        target = self.get(target_id)
        source = self.get(source_id)
        merged_ids = list(dict.fromkeys(
            list(target.get("game_ids", [])) + list(source.get("game_ids", []))
        ))
        self.storage.update_campaign(target_id, {"game_ids": merged_ids})
        self.delete(source_id)
        return self.get(target_id)

    def reorder(self, campaign_id: str, game_ids: list[str]) -> dict:
        coll = self.get(campaign_id)
        existing = set(coll.get("game_ids", []))
        ordered = [rid for rid in game_ids if rid in existing]
        # append any missing from original order
        for rid in coll.get("game_ids", []):
            if rid not in ordered:
                ordered.append(rid)
        return self.storage.update_campaign(campaign_id, {"game_ids": ordered})

    def counts(self) -> dict[str, int]:
        return {c.get("name", c.get("id", "?")): len(c.get("game_ids", [])) for c in self.list_all()}

    def render_list(self) -> str:
        cols = self.list_all()
        if not cols:
            return "No campaigns."
        lines = ["Campaigns:"]
        for c in cols:
            n = len(c.get("game_ids", []))
            lines.append(f"  - {c.get('name')} ({n} games)")
        return "\n".join(lines)

    def prune_stale_ids(self, campaign_id: str) -> int:
        coll = self.get(campaign_id)
        valid = []
        removed = 0
        for rid in coll.get("game_ids", []):
            try:
                self.storage.get_game(rid)
                valid.append(rid)
            except NotFoundError:
                removed += 1
        if removed:
            self.storage.update_campaign(campaign_id, {"game_ids": valid})
        return removed


# NightPlan grid lives in night_plan.py — storage-backed campaigns only here.
