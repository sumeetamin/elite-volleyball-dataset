import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from backfill_plusliga_2001_02 import parse_team_season_dates
import backfill_plusliga_2002_03 as backfill_2002_03


def test_team_season_dates_filter_to_2002_03_calendar_years():
    payload = b'''<div id="charttooltip2002001"><p class="date">30.09.2002, 18:00</p></div>
      <div id="charttooltip2002002"><p class="date">05.04.2003, 18:00</p></div>
      <div id="charttooltip2002003"><p class="date">04.10.2003, 18:00</p></div>'''
    assert parse_team_season_dates(payload, "2002/03") == {
        "2002001": "2002-09-30", "2002002": "2003-04-05",
    }


def test_2002_03_entrypoint_is_reusable_without_starting_download(monkeypatch):
    calls = []
    monkeypatch.setattr(backfill_2002_03,
                        "backfill_season",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, "argv", ["backfill_plusliga_2002_03.py"])
    backfill_2002_03.main()
    assert calls == [(("2002/03",), {
        "tour_id": 3, "expected_teams": 10, "expected_games_per_team": 18,
        "refresh": False,
    })]
