"""Import a browser capture of the official 1999/2000 Serie A1 men's calendar.

The source TSV is transcribed directly from the two official calendar phase pages.
Dates are intentionally blank: round headers are scheduled dates and some games
were rescheduled. A date should be added only after match-level verification.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from volleyball_dataset.import_italy import FIELDS  # noqa: E402

SOURCE = ROOT / "sources" / "italy_superlega_1999_2000_official_calendar.tsv"
SILVER = ROOT / "data" / "silver" / "italy_superlega_matches_2000_2026.csv"
COVERAGE = ROOT / "data" / "coverage_italy_superlega_historical.csv"
BASE = "https://ww2.legavolley.it/Calendario.asp?Anno=1999&IdCampionato=92&IdFase="


def read_capture() -> tuple[list[dict[str, str]], str]:
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        capture = list(csv.DictReader(stream, delimiter="\t"))
    if len(capture) != 132:
        raise ValueError(f"Expected 132 captured fixtures; got {len(capture)}")
    ids = [row["id_gara"] for row in capture]
    if len(set(ids)) != 132 or not all(item.isdecimal() for item in ids):
        raise ValueError("Official IdGara values must be 132 distinct integers")
    counts = Counter((row["phase"], row["round"]) for row in capture)
    if counts != Counter({(phase, str(round_no)): 6 for phase in ("Andata", "Ritorno") for round_no in range(1, 12)}):
        raise ValueError("Each phase must contain 11 rounds of six fixtures")
    teams = {row[side] for row in capture for side in ("home", "away")}
    appearances = Counter(team for row in capture for team in (row["home"], row["away"]))
    if len(teams) != 12 or set(appearances.values()) != {22}:
        raise ValueError("Expected twelve teams with 22 appearances each")
    meetings = Counter(tuple(sorted((row["home"], row["away"]))) for row in capture)
    if len(meetings) != 66 or set(meetings.values()) != {2}:
        raise ValueError("Expected each pair of teams to meet twice")

    rows = []
    for row in capture:
        score = re.fullmatch(r"([0-3])-([0-3])", row["score"])
        if not score or (int(score[1]) == 3) == (int(score[2]) == 3):
            raise ValueError(f"Invalid set score for IdGara {row['id_gara']}")
        phase_id = "1" if row["phase"] == "Andata" else "2"
        rows.append({
            "source": "Lega Volley official calendar browser capture",
            "source_match_id": row["id_gara"],
            "competition_key": "italy_superlega",
            "competition": "Italian SuperLega",
            "sex": "M",
            "season": "1999/2000",
            "round": f"{row['phase']} {row['round']}",
            "match_date": "",
            "home_team": row["home"],
            "away_team": row["away"],
            "home_sets": score[1],
            "away_sets": score[2],
            "status": "completed",
            "source_url": f"{BASE}{phase_id}&IdSquadra=0",
            "source_sha256": digest,
        })
    return rows, digest


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows, digest = read_capture()
    existing: list[dict[str, str]] = []
    if SILVER.exists():
        with SILVER.open(encoding="utf-8", newline="") as stream:
            existing = list(csv.DictReader(stream))
    merged = {(row["season"], row["source_match_id"]): row for row in existing}
    merged.update({(row["season"], row["source_match_id"]): row for row in rows})
    write_csv(SILVER, list(merged.values()), FIELDS)

    audit: list[dict[str, str]] = []
    fields: list[str] = []
    if COVERAGE.exists():
        with COVERAGE.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            fields = list(reader.fieldnames or [])
            audit = list(reader)
    if not fields:
        raise FileNotFoundError("Historical Italy coverage file is required")
    record = dict.fromkeys(fields, "")
    record.update({
        "competition_key": "italy_superlega",
        "competition": "Italian SuperLega",
        "sex": "M",
        "season": "1999/2000",
        "competition_id": "92",
        "participating_teams": "12",
        "expected_matches_double_round_robin": "132",
        "official_match_ids_observed": "132",
        "completed_results": "132",
        "result_coverage_pct": "100.0",
        "target_pct": "80",
        "target_met": "yes",
        "season_status": "completed",
        "scheduled_or_unresolved_matches": "0",
        "source_urls": f"{BASE}1&IdSquadra=0;{BASE}2&IdSquadra=0",
        "source_sha256": digest,
        "denominator_method": "12 official participants; 11 rounds x 6 fixtures x 2 phases; 132 unique IdGara",
    })
    audit = [row for row in audit if row["season"] != "1999/2000"]
    write_csv(COVERAGE, [record, *audit], fields)
    print(f"Imported 132 official results; silver now has {len(merged)} unique rows")


if __name__ == "__main__":
    main()
