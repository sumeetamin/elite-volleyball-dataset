"""Validate and normalize the browser-captured official PlusLiga 2011/12 schedule.

The archive's visible cards do not expose a match ID in the retained capture.
We therefore use a deterministic SHA-256 key over season/date/home/away and
explicitly label it as derived; it is not represented as an official ID.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://www.tauronliga.pl/games/tour/15.html"
SOURCE_FILE = ROOT / "data/bronze/plusliga_m_2011_12_official_results.tsv"
OUTPUT = ROOT / "data/silver/plusliga_m_2011_12_matches.csv"
COVERAGE = ROOT / "reports/plusliga_m_2011_12_browser_coverage.csv"
INVENTORY = ROOT / "reports/plusliga_m_2011_12_source_inventory.csv"
PROVENANCE = ROOT / "reports/plusliga_m_2011_12_provenance.md"
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
        raise ValueError(f"Expected 90 regular-season matches, got {len(rows)}")

    team_games: Counter[str] = Counter()
    seen: set[str] = set()
    normalized = []
    for row in rows:
        if row["phase"] != "Faza Zasadnicza":
            raise ValueError(f"Unexpected phase: {row['phase']}")
        match_date = date.fromisoformat("-".join(reversed(row["match_date"].split("."))))
        if not date(2011, 7, 1) <= match_date <= date(2012, 6, 30):
            raise ValueError(f"Out-of-season match date: {row['match_date']}")
        home, away = int(row["home_sets"]), int(row["away_sets"])
        if max(home, away) != 3 or min(home, away) not in {0, 1, 2}:
            raise ValueError(f"Invalid completed set result: {home}-{away}")
        home_team, away_team = row["home_team"].strip(), row["away_team"].strip()
        if not home_team or not away_team or home_team == away_team:
            raise ValueError("Invalid home/away team pair")
        identity = "|".join(("2011/12", match_date.isoformat(), home_team.casefold(), away_team.casefold()))
        if identity in seen:
            raise ValueError(f"Duplicate derived match key: {identity}")
        seen.add(identity)
        # Namespaced derived identity; not an official PLS match number.
        match_id = "derived-sha256:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
        team_games[home_team] += 1
        team_games[away_team] += 1
        normalized.append({
            "source": "Official PLS PlusLiga archive (browser DOM capture)",
            "source_match_id": match_id,
            "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
            "season": "2011/12", "phase": "regular_season",
            "match_date": match_date.isoformat(), "home_team": home_team, "away_team": away_team,
            "home_sets": str(home), "away_sets": str(away), "status": "completed",
            "source_url": SOURCE_URL, "source_sha256": digest,
            "date_source_url": SOURCE_URL, "date_source_sha256": digest,
        })
    if len(team_games) != 10 or set(team_games.values()) != {18}:
        raise ValueError(f"Expected 10 teams x 18 matches; found {dict(team_games)}")
    return normalized, digest


def main() -> None:
    matches, digest = normalize_capture()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(matches, key=lambda r: (r["match_date"], r["home_team"], r["away_team"])))

    coverage = {
        "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
        "season": "2011/12", "phase": "regular_season", "participating_teams": 10,
        "games_per_team": 18, "expected_matches": 90, "observed_matches": 90,
        "dated_matches": 90, "coverage_pct": 100.0, "date_coverage_pct": 100.0,
        "target_pct": 80, "target_met": "yes", "pair_pages_parsed": 0,
        "team_pages_parsed": 0, "standings_source_url": SOURCE_URL,
        "standings_source_sha256": digest,
        "denominator_method": "official archive: 18 regular-season rounds with five fixtures each; cross-check 10 teams x 18 matches / 2",
    }
    with COVERAGE.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(coverage))
        writer.writeheader(); writer.writerow(coverage)
    inventory = {
        "page_type": "official_regular_season_match_archive_dom_extract",
        "team_a_id": "", "team_b_id": "", "source_url": SOURCE_URL,
        "source_sha256": digest, "captured_at_utc": "2026-11-07",
        "parsed_rows": 90,
        "capture_method": "Browser DOM extraction; hash covers retained TSV, not upstream HTML; match keys are derived, not official IDs",
    }
    with INVENTORY.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(inventory))
        writer.writeheader(); writer.writerow(inventory)
    PROVENANCE.write_text(
        "# PlusLiga men 2011/12 regular-season backfill\n\n"
        f"Official archive: [{SOURCE_URL}]({SOURCE_URL}). Its season page rendered 18 regular-season rounds with five match cards each, 90 total, and displayed dates, home/away teams, and completed set scores.\n\n"
        "The captured records do not retain a visible official match ID. `source_match_id` is therefore a deterministic, namespaced SHA-256 identity derived from season/date/home/away; it is not claimed to be a PLS identifier. The bronze hash covers the retained browser extraction, not upstream HTML bytes. Cross-check: ten teams each appear in 18 regular-season matches (90 fixtures). All dates and scores validate.\n\n"
        f"Bronze extraction SHA-256: `{digest}`. Normalized outcomes: **90/90 (100%)**.\n",
        encoding="utf-8",
    )
    print(f"2011/12: {len(matches)}/90 results; derived IDs; extraction SHA-256 {digest}")


if __name__ == "__main__":
    main()
