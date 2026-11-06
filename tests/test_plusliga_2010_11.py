import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill_plusliga_2010_11 as backfill_2010_11


def test_2010_11_entrypoint_uses_official_tour_and_reconciliation(monkeypatch):
    calls = []
    monkeypatch.setattr(backfill_2010_11, "backfill_season",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, "argv", ["backfill_plusliga_2010_11.py"])
    backfill_2010_11.main()
    assert calls == [(("2010/11",), {
        "tour_id": 13, "expected_teams": 10, "expected_games_per_team": 18,
        "refresh": False, "detail_fallback": True,
    })]
