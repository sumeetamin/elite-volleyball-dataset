import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill_plusliga_2005_06 as backfill_2005_06
from backfill_plusliga_2001_02 import parse_team_season_dates


def test_team_season_dates_filter_to_2005_06_calendar_window():
    payload = b'''<div id="charttooltip2005001"><p class="date">15.10.2005, 18:00</p></div>
      <div id="charttooltip2005002"><p class="date">29.04.2006, 18:00</p></div>
      <div id="charttooltip2005003"><p class="date">01.09.2006, 18:00</p></div>'''
    assert parse_team_season_dates(payload, "2005/06") == {
        "2005001": "2005-10-15", "2005002": "2006-04-29",
    }


def test_2005_06_entrypoint_uses_official_tour_and_standings_gate(monkeypatch):
    calls = []
    monkeypatch.setattr(backfill_2005_06, "backfill_season",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, "argv", ["backfill_plusliga_2005_06.py"])
    backfill_2005_06.main()
    assert calls == [(("2005/06",), {
        "tour_id": 6, "expected_teams": 10, "expected_games_per_team": 18,
        "refresh": False,
    })]
