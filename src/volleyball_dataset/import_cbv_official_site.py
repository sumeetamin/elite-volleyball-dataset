"""Parse CBV's official 2025/26 Superliga match tables embedded in Next.js RSC."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

SEASON = "2025/26"
REGULAR_FIXTURES = 132  # 12 teams x 22 double-round-robin matches / 2
SOURCE = "CBV official Superliga website"
BASE = "https://cbv.com.br/volei-de-quadra/2025-2026/"
PAGES = {
    "M": BASE + "superliga-a-masculina",
    "F": BASE + "superliga-a-feminina",
}
MATCH_FIELDS = [
    "source", "source_match_id", "competition", "season", "sex", "competition_key",
    "phase", "round", "match_date", "match_datetime_source", "home_team", "away_team",
    "home_team_id", "away_team_id", "home_sets", "away_sets", "match_status",
    "source_match_number", "league_points_home", "league_points_away",
    *[f"set_{set_no}_{side}_points" for set_no in range(1, 6) for side in ("home", "away")],
    "spectators", "source_url", "source_sha256", "date_source_url", "date_source_sha256",
]


def parse_page(payload: bytes, sex: str, source_url: str) -> tuple[list[dict[str, object]], str]:
    """Return match rows and the HTML SHA-256; reject incomplete/ambiguous tables."""
    digest = hashlib.sha256(payload).hexdigest()
    soup = BeautifulSoup(payload, "html.parser")
    schedule = None
    for node in soup.find_all("script"):
        content = node.get_text()
        if "matchesByRound" not in content or "self.__next_f.push" not in content:
            continue
        wrapper = re.search(r"push\((\[.*\])\)", content, re.S)
        if not wrapper:
            continue
        chunk = json.loads(wrapper.group(1))[1]
        marker = 'matchesByRound":'
        start = chunk.find(marker)
        if start >= 0:
            schedule, _ = json.JSONDecoder().raw_decode(chunk, start + len(marker))
            break
    if schedule is None:
        raise ValueError("Official page lacks an embedded matchesByRound schedule")

    records = [match for round_group in schedule for matches in round_group.values() for match in matches]
    rows: dict[str, dict[str, object]] = {}
    for match in records:
        source_id = str(match.get("ChampionshipMatch_ID", "")).strip()
        number = int(match.get("MatchNumber", 0))
        raw_date = str(match.get("MatchDateTime", "")).strip()
        if not source_id or not number or not raw_date:
            raise ValueError("Official CBV row is missing match ID, match number, or date")
        home_sets, away_sets = match.get("WonSetHome"), match.get("WonSetGuest")
        completed = (isinstance(home_sets, int) and isinstance(away_sets, int)
                     and max(home_sets, away_sets) == 3 and min(home_sets, away_sets) in (0, 1, 2))
        row = {
            "source": SOURCE, "source_match_id": source_id,
            "competition": "Brazil Superliga", "season": SEASON, "sex": sex,
            "competition_key": "brazil_superliga",
            "phase": "regular_season" if number <= REGULAR_FIXTURES else "playoffs",
            "round": str(match.get("Round_Number", "")),
            # Source timestamp offsets are inconsistent with Brazil local time.
            # Preserve the literal, but use its official calendar date for day-level history.
            "match_date": raw_date[:10], "match_datetime_source": raw_date,
            "home_team": str(match.get("HomeTeam", "")).strip(),
            "away_team": str(match.get("GuestTeam", "")).strip(),
            "home_team_id": str(match.get("HomeTeam_ID", "")),
            "away_team_id": str(match.get("GuestTeam_ID", "")),
            "home_sets": home_sets if completed else "",
            "away_sets": away_sets if completed else "",
            "match_status": "completed" if completed else "scheduled",
            "source_match_number": str(match.get("MatchNumber", "")),
            "league_points_home": match.get("PointsHome", "") if completed else "",
            "league_points_away": match.get("PointsGuest", "") if completed else "",
            **{f"set_{set_no}_{side}_points": match.get(
                f"Set{set_no}{'Home' if side == 'home' else 'Guest'}", "") if completed else ""
               for set_no in range(1, 6) for side in ("home", "away")},
            "spectators": match.get("Spectators", "") or "",
            "source_url": source_url, "source_sha256": digest,
            "date_source_url": source_url, "date_source_sha256": digest,
        }
        old = rows.get(source_id)
        if old and old != row:
            raise ValueError(f"Conflicting CBV records for official match ID {source_id}")
        rows[source_id] = row

    if len(rows) != len(records):
        raise ValueError("Duplicate official match IDs in the embedded schedule")
    regular = [r for r in rows.values() if r["phase"] == "regular_season"]
    if len(regular) != REGULAR_FIXTURES:
        raise ValueError(f"Expected {REGULAR_FIXTURES} regular fixtures; found {len(regular)}")
    return sorted(rows.values(), key=lambda r: (r["phase"], r["match_date"], int(str(r["source_match_id"]))),), digest
