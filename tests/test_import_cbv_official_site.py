import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from volleyball_dataset.import_cbv_official_site import parse_page  # noqa: E402


def _page_payload(unplayed_last: bool = False) -> bytes:
    fixtures = []
    for number in range(1, 133):
        sets = (0, 0) if unplayed_last and number == 132 else (3, 1)
        fixtures.append({
            "ChampionshipMatch_ID": 3000000 + number, "MatchNumber": str(number),
            "HomeTeam_ID": 2000 + number, "GuestTeam_ID": 3000 + number,
            "HomeTeam": f"Home {number}", "GuestTeam": f"Away {number}",
            "WonSetHome": sets[0], "WonSetGuest": sets[1], "Round_Number": (number - 1) // 6 + 1,
            "PointsHome": 3, "PointsGuest": 0,
            "Set1Home": 25, "Set1Guest": 22,
            "MatchDateTime": f"2026-01-{(number - 1) % 28 + 1:02d}T20:00:00-03:00",
        })
    fixtures.append({
        "ChampionshipMatch_ID": 3000133, "MatchNumber": "133", "HomeTeam_ID": 1,
        "GuestTeam_ID": 2, "HomeTeam": "Playoff home", "GuestTeam": "Playoff away",
        "WonSetHome": 3, "WonSetGuest": 2, "Round_Number": 23,
        "MatchDateTime": "2026-04-01T20:00:00-03:00",
    })
    chunk = 'matchesByRound":' + json.dumps([{"TURNO": fixtures}], ensure_ascii=False)
    script = "self.__next_f.push(" + json.dumps([1, chunk], ensure_ascii=False) + ")"
    return f"<html><script>{script}</script></html>".encode("utf-8")


def test_cbv_official_page_imports_ids_dates_phase_and_unplayed_fixtures():
    rows, digest = parse_page(_page_payload(unplayed_last=True), "F", "https://official.invalid/women")
    regular = [row for row in rows if row["phase"] == "regular_season"]
    playoffs = [row for row in rows if row["phase"] == "playoffs"]
    assert len(regular) == 132
    assert sum(row["match_status"] == "completed" for row in regular) == 131
    assert next(row for row in regular if row["source_match_id"] == "3000132")["home_sets"] == ""
    assert regular[0]["home_team_id"] == "2001"
    assert regular[0]["match_date"] == "2026-01-01"
    assert regular[0]["match_datetime_source"].endswith("-03:00")
    assert regular[0]["set_1_home_points"] == 25
    assert regular[0]["league_points_home"] == 3
    assert len(playoffs) == 1 and playoffs[0]["match_status"] == "completed"
    assert all(row["source_sha256"] == digest for row in rows)


def test_cbv_official_page_rejects_missing_schedule():
    try:
        parse_page(b"<html><script>no match data</script></html>", "M", "https://official.invalid/men")
    except ValueError as exc:
        assert "lacks an embedded" in str(exc)
    else:
        raise AssertionError("invalid fixture schedule must be rejected")
