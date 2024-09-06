"""Tests for boardbox.migrate."""
import json
import pytest
from boardbox.errors import MigrationError
from boardbox.migrate import *

def test_detect_v0_list(v0_campaign_list):
    assert detect_version(v0_campaign_list) == 0

def test_migrate_v0_to_v3(v0_campaign_list):
    out = migrate_payload(v0_campaign_list, target=3)
    assert out['schema_version'] == 3
    assert out['games']

def test_migrate_v1_to_v3(v1_campaign_dict):
    out = migrate_payload(v1_campaign_dict, target=3)
    assert out['schema_version'] == 3

def test_migration_plan():
    componentlist = migration_plan(0, 3)
    assert len(componentlist) == 3

def test_migrate_file_missing(tmp_path):
    p = tmp_path / 'missing.json'
    result = migrate_file(str(p), target=3)
    assert result['schema_version'] == 3

def test_migrate_bad_v0():
    with pytest.raises(MigrationError):
        migrate_v0_to_v1(42)

def test_migrate_plan_v0_0():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_1():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_2():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_3():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_4():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_5():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_6():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v0_7():
    plan = migration_plan(0, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_0():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_1():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_2():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_3():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_4():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_5():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_6():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v1_7():
    plan = migration_plan(1, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_0():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_1():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_2():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_3():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_4():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_5():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_6():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v2_7():
    plan = migration_plan(2, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_0():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_1():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_2():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_3():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_4():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_5():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_6():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

def test_migrate_plan_v3_7():
    plan = migration_plan(3, 3)
    assert isinstance(plan, list)

