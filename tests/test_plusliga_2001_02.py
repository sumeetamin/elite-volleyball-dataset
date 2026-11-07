import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backfill_plusliga_2001_02 import merge_team_dates, parse_team_season_dates


def test_team_page_parser_reads_game_ids_and_exact_dates_only_for_requested_years():
    payload = b'''<div style="display:none">
      <div id="charttooltip1000005"><h4>Opponent A</h4><div class="khanded">3:1</div><p class="date">30.09.2001, 18:00</p></div>
      <div id="charttooltip1000006"><h4>Opponent B</h4><p class="date">07.10.2001, 19:00</p></div>
      <div id="charttooltip9999999"><h4>Current Opponent</h4><p class="date">30.09.2026, 19:00</p></div>
    </div>'''
    assert parse_team_season_dates(payload) == {
        "1000005": "2001-09-30", "1000006": "2001-10-07",
    }


def test_date_join_uses_official_match_id_and_preserves_other_phase():
    matches = {
        "1000005": {"source_match_id": "1000005", "phase": "regular_season", "match_date": ""},
        "1000006": {"source_match_id": "1000006", "phase": "playoffs", "match_date": ""},
    }
    dated = merge_team_dates(matches, {"1000005": "2001-09-30"})
    assert dated == 1
    assert matches["1000005"]["match_date"] == "2001-09-30"
    assert matches["1000006"]["match_date"] == ""


def test_date_join_rejects_team_page_id_absent_from_pair_archive():
    matches = {"1": {"source_match_id": "1", "phase": "regular_season", "match_date": ""}}
    try:
        merge_team_dates(matches, {"2": "2001-09-30"})
    except ValueError as exc:
        assert "absent from pair archive" in str(exc)
    else:
        raise AssertionError("unmatched official ID should fail the reconciliation")
