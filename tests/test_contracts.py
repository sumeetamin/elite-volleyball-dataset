import pandas as pd
import pytest
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
from volleyball_dataset.contracts import validate_tables
from volleyball_dataset.normalize import stable_match_id, to_utc
from volleyball_dataset.coverage_audit import build_coverage

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

def test_uncollected_source_is_not_reported_as_zero_coverage():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory = root / "inventory.csv"
        with inventory.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["competition_key", "competition", "sex", "season", "expected_matches", "target_pct"])
            writer.writeheader()
            writer.writerow(dict(competition_key="brazil_superliga", competition="Brazil", sex="M", season="2024/25", expected_matches="132", target_pct="80"))
            writer.writerow(dict(competition_key="cev_cl", competition="CEV", sex="M", season="2024/25", expected_matches="100", target_pct="80"))
        silver = root / "silver"
        silver.mkdir()
        with (silver / "cbv_superliga_matches.csv").open("w", newline="", encoding="utf-8") as f:
            f.write("competition_key,season,sex,phase,match_status\n")
        rows = build_coverage(inventory, root)
    assert rows[0]["observed_status"] == "zero_records_in_available_file"
    assert rows[0]["observed_matches"] == ""
    assert rows[0]["coverage_pct"] == ""
    assert rows[1]["observed_status"] == "source_not_collected"
    assert rows[1]["observed_matches"] == ""
    assert rows[1]["coverage_pct"] == ""
