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

def test_cev_women_long_season_label_maps_to_inventory_division():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory = root / "inventory.csv"
        with inventory.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["competition_key", "competition", "sex", "season", "expected_matches", "target_pct"])
            writer.writeheader()
            writer.writerow(dict(competition_key="cev_cl", competition="CEV Champions League", sex="F", season="2000/01", expected_matches="", target_pct="80"))
        silver = root / "silver"
        silver.mkdir()
        (silver / "cev_champions_league_matches.csv").write_text(
            "gender,season_name,sets_a,sets_b\nW,EUROPEAN CHAMPIONS LEAGUE WOMEN - 2000/2001,3,1\nW,EUROPEAN CHAMPIONS LEAGUE WOMEN - 2000/2001,2,2\n",
            encoding="utf-8",
        )
        rows = build_coverage(inventory, root)
    assert rows[0]["observed_matches"] == 1
    assert rows[0]["observed_status"] == "records_found"
    assert rows[0]["coverage_pct"] == ""
    assert rows[0]["denominator_status"] == "unknown"

def test_fivb_annual_lineage_counts_results_and_excludes_qualifiers():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        inventory = root / "inventory.csv"
        with inventory.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["competition_key", "competition", "sex", "season", "expected_matches", "target_pct"])
            writer.writeheader()
            for sex, season in [("M", "World League 2010"), ("F", "World Grand Prix 2010"), ("M", "VNL 2024"), ("F", "VNL 2024")]:
                writer.writerow(dict(competition_key="vnl", competition="International League", sex=sex, season=season, expected_matches="", target_pct="80"))
        silver = root / "silver"
        silver.mkdir()
        fields = ["match_id", "competition_name", "edition_year", "gender", "status", "sets_a", "sets_b"]
        rows = [
            ["m1", "World League 2010", "2010", "M", "Closed", "3", "1"],
            ["m1", "World League 2010", "2010", "M", "Closed", "3", "1"],  # duplicate source ID
            ["q1", "World League 2011 - Qualification Tournaments", "2010", "M", "Closed", "3", "0"],
            ["old1", "World League 2009", "2010", "M", "Result is official", "3", "0"],
            ["pending", "World League 2010", "2010", "M", "Scheduled", "", ""],
            ["w1", "World Grand Prix 2010 - 1st Group", "2010", "W", "Result is official", "3", "2"],
            ["vm1", "Men's Volleyball Nations League 2024", "2024", "M", "Result is official", "3", "1"],
            ["vf1", "Women's Volleyball Nations League 2024", "2024", "W", "Result is official", "3", "2"],
            ["test1", "VNL 2024 - WOMEN (TEST ONLY)", "2024", "W", "Finished", "3", "0"],
            ["cava1", "CAVA Nations League 2024", "2024", "M", "Result is official", "3", "0"],
        ]
        with (silver / "fivb_vis_matches.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(fields); writer.writerows(rows)
        report = build_coverage(inventory, root)
    assert [r["observed_matches"] for r in report] == [1, 1, 1, 1]
    assert all(r["coverage_pct"] == "" and r["denominator_status"] == "unknown" for r in report)
