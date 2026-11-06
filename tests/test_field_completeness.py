import csv
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from volleyball_dataset.field_completeness import audit_table  # noqa: E402


def test_field_audit_distinguishes_absent_fields_from_zero_coverage():
    with TemporaryDirectory() as temp:
        path = Path(temp) / "example.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[
                "competition_key", "sex", "season", "source_match_id", "match_date",
                "home_team", "away_team", "home_sets", "away_sets", "set_1_home_points",
                "scoresheet_url",
            ])
            writer.writeheader()
            writer.writerows([
                {"competition_key": "test", "sex": "M", "season": "2025/26", "source_match_id": "1",
                 "match_date": "2025-10-01", "home_team": "A", "away_team": "B", "home_sets": 3,
                 "away_sets": 1, "set_1_home_points": 25, "scoresheet_url": "https://official.invalid/1.pdf"},
                {"competition_key": "test", "sex": "M", "season": "2025/26", "source_match_id": "2",
                 "match_date": "2025-10-02", "home_team": "A", "away_team": "C", "home_sets": "",
                 "away_sets": "", "set_1_home_points": "", "scoresheet_url": ""},
            ])
        rows = {row["field_group"]: row for row in audit_table(path)}
    assert rows["match_result"]["rows_with_data"] == 1
    assert rows["match_result"]["coverage_pct"] == 50.0
    assert rows["set_points"]["coverage_pct"] == 50.0
    assert rows["odds_data"]["coverage_pct"] == ""
    assert rows["odds_data"]["availability"] == "not_in_imported_schema"
    assert rows["official_scoresheet_link"]["coverage_pct"] == 50.0
