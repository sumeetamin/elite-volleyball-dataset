import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill_plusliga_2004_05 as backfill_2004_05
from backfill_plusliga_2001_02 import parse_team_season_dates


def test_team_season_dates_filter_to_2004_05_calendar_window():
    payload = b'''<div id="charttooltip2004001"><p class="date">16.10.2004, 18:00</p></div>
      <div id="charttooltip2004002"><p class="date">30.04.2005, 18:00</p></div>
      <div id="charttooltip2004003"><p class="date">01.09.2005, 18:00</p></div>'''
    assert parse_team_season_dates(payload, "2004/05") == {
        "2004001": "2004-10-16", "2004002": "2005-04-30",
    }


def test_2004_05_entrypoint_uses_official_tour_and_standings_gate(monkeypatch):
    calls = []
    monkeypatch.setattr(backfill_2004_05, "backfill_season",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, "argv", ["backfill_plusliga_2004_05.py"])
    backfill_2004_05.main()
    assert calls == [(("2004/05",), {
        "tour_id": 5, "expected_teams": 10, "expected_games_per_team": 18,
        "refresh": False,
    })]
