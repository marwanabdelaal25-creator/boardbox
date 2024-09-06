"""Tests for boardbox.night_plan."""

from datetime import date

import pytest

from boardbox.errors import CampaignError, NotFoundError
from boardbox.play_log import SessionContext
from boardbox.night_plan import NightPlan, NightPlanCampaign


def test_night_plan_assign_and_copy():
    plan = NightPlan(date(2024, 6, 5))
    plan.assign("rec001", plan.week_start, SessionContext.DINNER, year_override=4)
    assert plan.count_filled_slots() == 1
    assert plan.all_meals()[0].game_id == "rec001"
    copy = plan.copy_to_week(plan.week_start)
    assert copy.count_filled_slots() >= 1
    assert plan.format_grid()


def test_night_plan_campaign():
    plan = NightPlan(date(2024, 6, 5))
    coll = NightPlanCampaign()
    coll.add(plan)
    assert coll.get(plan.id) is plan
    assert coll.get_or_create(plan.week_start).id == plan.id
    restored = NightPlanCampaign.from_dict(coll.to_dict())
    assert restored.all()


def test_night_plan_errors():
    plan = NightPlan(date(2024, 6, 5))
    with pytest.raises(CampaignError):
        plan.assign("rec001", date(1999, 1, 1), SessionContext.BREAKFAST)
    with pytest.raises(NotFoundError):
        plan.require(plan.week_start, SessionContext.LUNCH)
