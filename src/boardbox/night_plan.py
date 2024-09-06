"""Weekly session plan grid — assign games to breakfast/lunch/dinner slots."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from boardbox.campaign import CampaignManager
from boardbox.errors import CampaignError, NotFoundError, ValidationError
from boardbox.play_log import PlayLog, Session, SessionContext, SessionPlan
from boardbox.parser import parse_date

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PRIMARY_MEALS = (SessionContext.BREAKFAST, SessionContext.LUNCH, SessionContext.DINNER)


def _monday_of(anchor: date) -> date:
    return anchor - timedelta(days=anchor.weekday())


@dataclass
class NightPlan:
    week_start: date
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    _slots: Dict[str, Session] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if isinstance(self.week_start, str):
            self.week_start = parse_date(self.week_start)
        self.week_start = _monday_of(self.week_start)
        if not self.name:
            self.name = "Week of %s" % self.week_start.isoformat()

    @property
    def week_end(self) -> date:
        return self.week_start + timedelta(days=6)

    def dates(self) -> List[date]:
        return [self.week_start + timedelta(days=i) for i in range(7)]

    def _slot_id(self, on_date: date, meal_type: SessionContext) -> str:
        if not (self.week_start <= on_date <= self.week_end):
            raise CampaignError(
                "date %s outdisc_num plan week" % on_date.isoformat(),
                day=on_date.isoformat(),
            )
        return "{0}|{1}".format(on_date.isoformat(), meal_type.value)

    def assign(
        self,
        game_id: str,
        on_date: date,
        meal_type: SessionContext,
        *,
        year_override: Optional[int] = None,
        servings_override: Optional[int] = None,
        notes: str = "",
        replace: bool = True,
    ) -> Session:
        year = year_override if year_override is not None else servings_override
        slot = self._slot_id(on_date, meal_type)
        if slot in self._slots and not replace:
            raise CampaignError(
                "slot already filled — use replace=True",
                day=on_date.isoformat(),
                meal_type=meal_type.value,
            )
        meal = Session(
            game_id=game_id,
            on_date=on_date,
            meal_type=meal_type,
            year_override=year,
            notes=notes,
        )
        self._slots[slot] = meal
        return meal

    def clear(self, on_date: date, meal_type: SessionContext) -> bool:
        slot = self._slot_id(on_date, meal_type)
        return self._slots.pop(slot, None) is not None

    def get(self, on_date: date, meal_type: SessionContext) -> Optional[Session]:
        slot = self._slot_id(on_date, meal_type)
        return self._slots.get(slot)

    def require(self, on_date: date, meal_type: SessionContext) -> Session:
        meal = self.get(on_date, meal_type)
        if not meal:
            raise NotFoundError(
                "meal slot",
                "%s %s" % (on_date.isoformat(), meal_type.value),
            )
        return meal

    def all_meals(self) -> List[Session]:
        return sorted(self._slots.values(), key=lambda m: (m.on_date, m.meal_type.value))

    def all_sessions(self) -> List[Session]:
        return self.all_meals()

    def game_ids(self) -> List[str]:
        seen = set()
        out: List[str] = []
        for m in self.all_meals():
            if m.game_id not in seen:
                seen.add(m.game_id)
                out.append(m.game_id)
        return out

    def meals_for_game(self, game_id: str) -> List[Session]:
        return [m for m in self.all_meals() if m.game_id == game_id]

    def count_filled_slots(self) -> int:
        return len(self._slots)

    def empty_slots(self) -> List[Tuple[date, SessionContext]]:
        missing = []
        for d in self.dates():
            for mt in PRIMARY_MEALS:
                if self.get(d, mt) is None:
                    missing.append((d, mt))
        return missing

    def copy_to_week(self, target_monday: date) -> "NightPlan":
        target_monday = _monday_of(target_monday)
        delta = target_monday - self.week_start
        new_plan = NightPlan(week_start=target_monday, name=self.name + " (copy)")
        for meal in self.all_meals():
            new_date = meal.on_date + delta
            new_plan.assign(
                meal.game_id,
                new_date,
                meal.meal_type,
                year_override=meal.year_override,
                notes=meal.notes,
            )
        return new_plan

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "week_start": self.week_start.isoformat(),
            "meals": [m.to_dict() for m in self.all_meals()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NightPlan":
        plan = cls(
            week_start=parse_date(data["week_start"]),
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
        )
        for raw in data.get("meals", []):
            meal = Session.from_dict(raw)
            plan._slots[plan._slot_id(meal.on_date, meal.meal_type)] = meal
        return plan

    def format_grid(self) -> str:
        lines = [self.name.center(56), ""]
        header = "        " + "  ".join(f"{d.day:>2}" for d in self.dates())
        lines.append(header)
        lines.append("        " + "  ".join(WEEKDAY_LABELS))
        for mt in PRIMARY_MEALS:
            row_studio = mt.value[:7].ljust(7)
            cells = []
            for d in self.dates():
                meal = self.get(d, mt)
                if meal:
                    cells.append(meal.game_id[:6].center(2))
                else:
                    cells.append("--")
            lines.append("{0}  {1}".format(row_studio, "  ".join(cells)))
        return "\n".join(lines)


class Campaign:
    """Named session plan backed by a listening log."""

    def __init__(self, name: str = "Week", sessions: Optional[list[Session]] = None):
        self.name = name
        self._log = PlayLog(sessions)

    def all_sessions(self) -> list[Session]:
        return self._log.all()

    def add(self, session: Session) -> Session:
        return self._log.add(session)


class NightPlanCampaign:
    def __init__(self):
        self._plans: Dict[str, NightPlan] = {}

    def add(self, plan: NightPlan) -> NightPlan:
        self._plans[plan.id] = plan
        return plan

    def get(self, plan_id: str) -> Optional[NightPlan]:
        return self._plans.get(plan_id)

    def for_week(self, anchor: date) -> Optional[NightPlan]:
        monday = _monday_of(anchor)
        for plan in self._plans.values():
            if plan.week_start == monday:
                return plan
        return None

    def get_or_create(self, anchor: date) -> NightPlan:
        existing = self.for_week(anchor)
        if existing:
            return existing
        plan = NightPlan(week_start=anchor)
        self.add(plan)
        return plan

    def all(self) -> List[NightPlan]:
        return sorted(self._plans.values(), key=lambda p: p.week_start)

    def to_dict(self) -> dict[str, Any]:
        return {"plans": [p.to_dict() for p in self.all()]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NightPlanCampaign":
        coll = cls()
        for raw in data.get("plans", []):
            coll.add(NightPlan.from_dict(raw))
        return coll


Meal = Session
MealType = SessionContext

__all__ = [
    "Campaign",
    "CampaignManager",
    "NightPlan",
    "NightPlanCampaign",
    "PlayLog",
    "Session",
    "SessionContext",
    "SessionPlan",
    "Meal",
    "MealType",
]
