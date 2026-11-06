import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backfill_plusliga_2009_10 as backfill_2009_10


def test_2009_10_entrypoint_uses_verified_tour_and_reconciliation(monkeypatch):
    calls = []
    monkeypatch.setattr(backfill_2009_10, "backfill_season",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(sys, "argv", ["backfill_plusliga_2009_10.py"])
    backfill_2009_10.main()
    assert calls == [(("2009/10",), {
        "tour_id": 11, "expected_teams": 10, "expected_games_per_team": 18,
        "refresh": False, "detail_fallback": True,
    })]
