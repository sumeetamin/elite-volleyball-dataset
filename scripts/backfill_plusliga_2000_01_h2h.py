"""Recover official PlusLiga 2000/01 scores from the league's matchup archive.

The website exposes all-time results for each team pair rather than a single
season results page. The inaugural participant set is taken from the league's
own 25-year history article. Raw requests and normalized results remain local
until source redistribution terms have been reviewed.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from volleyball_dataset.import_polish_head_to_head import (  # noqa: E402
    FIELDS,
    parse_head_to_head_page,
    parse_official_season_roster,
)

BASE = "https://www.plusliga.pl/statsTeams/teams_1/{team_a}/teams_2/{team_b}/type/teamsComparator/nocookies/1.html"
ROSTER_SOURCE = "https://www.plusliga.pl/table/tour/1/nocookies/1.html"
ROSTER_RAW = ROOT / "data" / "bronze" / "plusliga_m_2000_01_final_table.html"
RAW_DIR = ROOT / "data" / "bronze"
OUTPUT = ROOT / "data" / "silver" / "plusliga_m_2000_01_head_to_head.csv"
REPORT = ROOT / "reports" / "plusliga_m_2000_01_h2h_coverage_2026-11-06.csv"
SOURCE_REPORT = ROOT / "reports" / "plusliga_m_2000_01_h2h_source_inventory_2026-11-06.csv"


def fetch_pair(pair: tuple[str, str]) -> tuple[str, str, bytes]:
    team_a, team_b = pair
    url = BASE.format(team_a=team_a, team_b=team_b)
    raw_path = RAW_DIR / f"plusliga_m_2000_01_h2h_{team_a}_{team_b}.html"
    if raw_path.exists():
        return url, str(raw_path), raw_path.read_bytes()
    req = Request(url, headers={"User-Agent": "EliteVolleyballDataset/0.1 (historical research)"})
    with urlopen(req, timeout=40) as response:
        payload = response.read()
    raw_path.write_bytes(payload)
    time.sleep(0.3)
    return url, str(raw_path), payload


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def backfill() -> tuple[int, int]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ROSTER_RAW.exists():
        roster_payload = ROSTER_RAW.read_bytes()
    else:
        request = Request(ROSTER_SOURCE, headers={"User-Agent": "EliteVolleyballDataset/0.1 (historical research)"})
        with urlopen(request, timeout=40) as response:
            roster_payload = response.read()
        ROSTER_RAW.write_bytes(roster_payload)
        time.sleep(0.3)
    roster = parse_official_season_roster(roster_payload)
    team_ids = sorted(roster, key=int)
    games_played = {int(info["matches_played"]) for info in roster.values()}
    if len(games_played) != 1:
        raise ValueError(f"Final regular-season standings have inconsistent played-game counts: {games_played}")
    pairs = list(itertools.combinations(team_ids, 2))
    matches: dict[str, dict[str, object]] = {}
    coverage_sources: list[dict[str, object]] = []
    retrieved = datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_pair, pair): pair for pair in pairs}
        for future in as_completed(futures):
            url, raw_path_text, payload = future.result()
            raw_path = Path(raw_path_text)
            page_rows = parse_head_to_head_page(payload, url, "plusliga", "2000/01", "M")
            for row in page_rows:
                previous = matches.get(str(row["source_match_id"]))
                if previous and (previous["home_team"], previous["away_team"], previous["home_sets"], previous["away_sets"]) != (row["home_team"], row["away_team"], row["home_sets"], row["away_sets"]):
                    raise ValueError(f"Conflicting result for official PlusLiga ID {row['source_match_id']}")
                matches[str(row["source_match_id"])] = row
            coverage_sources.append({
                "competition_key": "plusliga", "sex": "M", "season": "2000/01",
                "team_a_id": futures[future][0], "team_b_id": futures[future][1],
                "team_a_name": roster[futures[future][0]]["team_name"],
                "team_b_name": roster[futures[future][1]]["team_name"],
                "source_url": url, "source_sha256": hashlib.sha256(payload).hexdigest(),
                "captured_at_utc": datetime.fromtimestamp(raw_path.stat().st_mtime, timezone.utc).isoformat(),
                "roster_source_url": ROSTER_SOURCE,
                "roster_source_sha256": hashlib.sha256(roster_payload).hexdigest(),
                "rows_for_season": len(page_rows),
            })

    ordered = sorted(matches.values(), key=lambda r: (str(r["phase"]), int(str(r["source_match_id"]))))
    _write_csv(OUTPUT, FIELDS, ordered)
    regular = [r for r in ordered if r["phase"] == "regular_season"]
    playoffs = [r for r in ordered if r["phase"] == "playoffs"]
    playouts = [r for r in ordered if r["phase"] == "playouts"]
    expected_regular = len(roster) * next(iter(games_played)) // 2
    # The official final table lists each participating team's regular-season
    # games played; the unique H2H archive has one row per completed match.
    coverage_rows = [
        {"competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
         "season": "2000/01", "phase": "regular_season", "participating_teams": len(roster),
         "games_per_team": next(iter(games_played)), "expected_matches": expected_regular,
         "observed_matches": len(regular), "coverage_pct": round(100 * len(regular) / expected_regular, 4),
         "target_pct": 80, "target_met": "yes" if len(regular) / expected_regular >= .8 else "no",
         "source_count": len(coverage_sources), "source_sha256_values": ";".join(x["source_sha256"] for x in coverage_sources),
         "source_urls": ";".join(x["source_url"] for x in coverage_sources),
         "roster_source_url": ROSTER_SOURCE, "roster_source_sha256": hashlib.sha256(roster_payload).hexdigest(),
         "denominator_method": "official final regular-season standings list participating teams and games played; expected matches = sum(team games played) / 2"},
        {"competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
         "season": "2000/01", "phase": "playoffs", "participating_teams": len(roster),
         "games_per_team": "", "expected_matches": "",
         "observed_matches": len(playoffs), "coverage_pct": "", "target_pct": 80,
         "target_met": "", "source_count": len(coverage_sources),
         "source_sha256_values": ";".join(x["source_sha256"] for x in coverage_sources),
         "source_urls": ";".join(x["source_url"] for x in coverage_sources),
         "roster_source_url": ROSTER_SOURCE, "roster_source_sha256": hashlib.sha256(roster_payload).hexdigest(),
         "denominator_method": "playoff outcomes retained separately; official historical playoff fixture denominator not yet audited"},
        {"competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
         "season": "2000/01", "phase": "playouts", "participating_teams": len(roster),
         "games_per_team": "", "expected_matches": "", "observed_matches": len(playouts),
         "coverage_pct": "", "target_pct": 80, "target_met": "", "source_count": len(coverage_sources),
         "source_sha256_values": ";".join(x["source_sha256"] for x in coverage_sources),
         "source_urls": ";".join(x["source_url"] for x in coverage_sources),
         "roster_source_url": ROSTER_SOURCE, "roster_source_sha256": hashlib.sha256(roster_payload).hexdigest(),
         "denominator_method": "play-out results retained separately; official fixture denominator not yet audited"},
    ]
    _write_csv(REPORT, list(coverage_rows[0]), coverage_rows)
    _write_csv(SOURCE_REPORT, list(coverage_sources[0]), coverage_sources)
    _write_csv(ROOT / "data" / "coverage_plusliga_2000_01_pair_sources.csv", list(coverage_sources[0]), coverage_sources)
    print(f"regular season: {len(regular)}/{expected_regular}; playoffs observed: {len(playoffs)}; play-outs observed: {len(playouts)}; total unique IDs: {len(ordered)}")
    return len(regular), len(ordered)


if __name__ == "__main__":
    backfill()
