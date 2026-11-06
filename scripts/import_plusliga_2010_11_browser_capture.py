"""Validate and normalize the captured official PlusLiga 2010/11 match ledger.

The source page was opened and extracted in a browser because workspace DNS
cannot reach its host. The bronze TSV is the retained extraction; its SHA-256
is therefore the extraction-payload hash, not a claim to hash the page HTML.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.tauronliga.pl/games/tour/13.html"
SOURCE_FILE = ROOT / "data/bronze/plusliga_m_2010_11_official_results.tsv"
OUTPUT = ROOT / "data/silver/plusliga_m_2010_11_matches.csv"
COVERAGE = ROOT / "reports/plusliga_m_2010_11_coverage.csv"
INVENTORY = ROOT / "reports/plusliga_m_2010_11_source_inventory.csv"
PROVENANCE = ROOT / "reports/plusliga_m_2010_11_provenance.md"
FIELDS = ["source", "source_match_id", "competition_key", "competition", "sex",
          "season", "phase", "match_date", "home_team", "away_team", "home_sets",
          "away_sets", "status", "source_url", "source_sha256", "date_source_url",
          "date_source_sha256"]


def normalize_capture(path: Path = SOURCE_FILE) -> tuple[list[dict[str, str]], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(rows) != 90:
        raise ValueError(f"Expected 90 official regular-season rows, got {len(rows)}")
    ids = [row["source_match_id"].strip() for row in rows]
    if any(not match_id for match_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Official match IDs must be nonempty and unique")

    team_games: Counter[str] = Counter()
    normalized = []
    for row in rows:
        if row["phase"] != "Faza Zasadnicza":
            raise ValueError(f"Unexpected phase for match {row['source_match_id']}: {row['phase']}")
        match_date = datetime.strptime(row["match_datetime"], "%d.%m.%Y, %H:%M")
        if not datetime(2010, 7, 1) <= match_date <= datetime(2011, 6, 30, 23, 59):
            raise ValueError(f"Out-of-season date for match {row['source_match_id']}")
        home, away = int(row["home_sets"]), int(row["away_sets"])
        if max(home, away) != 3 or min(home, away) not in {0, 1, 2}:
            raise ValueError(f"Invalid completed volleyball result for match {row['source_match_id']}")
        if not row["home_team"].strip() or not row["away_team"].strip() or row["home_team"] == row["away_team"]:
            raise ValueError(f"Invalid teams for match {row['source_match_id']}")
        team_games[row["home_team"]] += 1
        team_games[row["away_team"]] += 1
        normalized.append({
            "source": "Official PLS PlusLiga match archive (browser DOM extract)",
            "source_match_id": row["source_match_id"],
            "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
            "season": "2010/11", "phase": "regular_season",
            "match_date": match_date.date().isoformat(),
            "home_team": row["home_team"], "away_team": row["away_team"],
            "home_sets": str(home), "away_sets": str(away), "status": "completed",
            "source_url": SOURCE_URL, "source_sha256": digest,
            "date_source_url": SOURCE_URL, "date_source_sha256": digest,
        })
    if len(team_games) != 10 or set(team_games.values()) != {18}:
        raise ValueError(f"Expected 10 teams with 18 regular matches each, got {dict(team_games)}")
    return normalized, digest


def main() -> None:
    matches, digest = normalize_capture()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(matches, key=lambda row: (row["match_date"], int(row["source_match_id"]))))

    coverage_row = {
        "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
        "season": "2010/11", "phase": "regular_season", "participating_teams": 10,
        "games_per_team": 18, "expected_matches": 90, "observed_matches": 90,
        "dated_matches": 90, "coverage_pct": 100.0, "date_coverage_pct": 100.0,
        "target_pct": 80, "target_met": "yes", "pair_pages_parsed": 0,
        "team_pages_parsed": 0, "standings_source_url": SOURCE_URL,
        "standings_source_sha256": digest,
        "denominator_method": "official archive roster: 10 teams x 18 regular-season matches/team / 2",
    }
    with COVERAGE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(coverage_row))
        writer.writeheader(); writer.writerow(coverage_row)
    inventory_row = {
        "page_type": "official_regular_season_match_archive_dom_extract",
        "team_a_id": "", "team_b_id": "", "source_url": SOURCE_URL,
        "source_sha256": digest, "captured_at_utc": "2026-11-07",
        "parsed_rows": 90, "capture_method": "Browser DOM extraction; hash covers retained TSV, not upstream HTML",
    }
    with INVENTORY.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(inventory_row))
        writer.writeheader(); writer.writerow(inventory_row)
    PROVENANCE.write_text(
        "# PlusLiga men 2010/11 regular-season backfill\n\n"
        f"Official archive: [{SOURCE_URL}]({SOURCE_URL}). It rendered 90 completed regular-season match cards with unique official IDs, dates, home/away teams, and set scores.\n\n"
        "The local bronze TSV retains the extracted table fields. Its SHA-256 is the hash of that retained extraction, not the upstream HTML; raw page bytes were unavailable because direct workspace DNS access is blocked. The official schedule denominator is 10 teams x 18 matches/team / 2 = 90. Every team appears 18 times; all 90 rows have valid completed scores and exact dates.\n\n"
        f"Bronze extraction SHA-256: `{digest}`. Normalized rows: **90/90 (100%)**.\n",
        encoding="utf-8",
    )
    print(f"2010/11: {len(matches)}/90 unique, dated regular-season outcomes; extraction SHA-256 {digest}")


if __name__ == "__main__":
    main()
