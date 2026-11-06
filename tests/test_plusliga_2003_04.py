import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill_plusliga_2003_04 as backfill_2003_04
from backfill_plusliga_2001_02 import parse_team_season_dates


def test_team_season_dates_filter_to_2003_04_calendar_window():
    payload = b'''<div id="charttooltip2003001"><p class="date">18.10.2003, 18:00</p></div>
      <div id="charttooltip2003002"><p class="date">20.03.2004, 18:00</p></div>
      <div id="charttooltip2003003"><p class="date">12.09.2004, 18:00</p></div>'''
    assert parse_team_season_dates(payload, "2003/04") == {
        "2003001": "2003-10-18", "2003002": "2004-03-20",
    }


def test_2003_04_entrypoint_uses_official_tour_and_standings_gate(monkeypatch):
    calls = []
    monkeypatch.setattr(backfill_2003_04, "backfill_season",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, "argv", ["backfill_plusliga_2003_04.py"])
    backfill_2003_04.main()
    assert calls == [(("2003/04",), {
        "tour_id": 4, "expected_teams": 10, "expected_games_per_team": 18,
        "refresh": False,
    })]
