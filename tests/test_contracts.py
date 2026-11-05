import pandas as pd
import pytest
from volleyball_dataset.contracts import validate_tables
from volleyball_dataset.normalize import stable_match_id, to_utc

def test_stable_ids_require_source_id():
    assert stable_match_id("fivb","123") == "FIVB_123"
    with pytest.raises(ValueError): stable_match_id("fivb","")

def test_naive_time_is_rejected():
    with pytest.raises(ValueError): to_utc("2025-01-01 12:00")
    assert str(to_utc("2025-01-01T12:00:00+02:00")) == "2025-01-01 10:00:00+00:00"

def test_contract_accepts_minimal_empty_children():
    matches=pd.DataFrame([dict(match_id="x",team_a_id="a",team_b_id="b",status="scheduled")])
    assert validate_tables(matches,pd.DataFrame(),pd.DataFrame()) == []

def test_contract_detects_duplicate_and_orphan():
    matches=pd.DataFrame([dict(match_id="x",team_a_id="a",team_b_id="b",status="scheduled")])
    sets=pd.DataFrame([dict(match_id="missing",set_number=1),dict(match_id="missing",set_number=1)])
    problems=validate_tables(matches,sets,pd.DataFrame())
    assert any("duplicate key" in p for p in problems)
    assert any("orphan match IDs" in p for p in problems)

def test_completed_set_requires_win_by_two():
    matches=pd.DataFrame([dict(match_id="x",team_a_id="a",team_b_id="b",status="completed",sets_a=3,sets_b=0)])
    sets=pd.DataFrame([dict(match_id="x",set_number=1,points_a=25,points_b=24,completed=True)])
    assert any("invalid completed score" in p for p in validate_tables(matches,sets,pd.DataFrame()))
