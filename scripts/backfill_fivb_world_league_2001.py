"""Normalize the complete 2001 men's World League result table.

The captured Newikis/Wikipedia table is cross-reconciled against the archived
OSSCG federation match listings. The importer retains result-level data only:
one archived set-point string conflicts with the published table, so set
points are omitted from silver.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/fivb_world_league_2001_match_table.tsv"
OUTPUT = ROOT / "data/silver/fivb_legacy_world_league_2001_matches.csv"
ARCHIVE_URL = "https://web.archive.org/web/20080516194949/http://www.osscg.org.yu/volleyball_WL2005/2_historyWL_2001.asp"
TABLE_URL = "https://newikis.com/en/2001_FIVB_Volleyball_World_League"
TEAM_CODES = {
    "Argentina": "ARG", "Brazil": "BRA", "Cuba": "CUB", "France": "FRA",
    "Germany": "GER", "Greece": "GRE", "FR Yugoslavia": "YUG", "Italy": "ITA",
    "Japan": "JPN", "Netherlands": "NED", "Poland": "POL", "Portugal": "POR",
    "Russia": "RUS", "Spain": "ESP", "United States": "USA", "Venezuela": "VEN",
}
FIELDS = [
    "competition_key", "competition_name", "season", "gender", "match_id",
    "match_date", "phase", "team_a_code", "team_a_name", "team_b_code",
    "team_b_name", "sets_a", "sets_b", "result_text", "set_1_a", "set_1_b",
    "set_2_a", "set_2_b", "set_3_a", "set_3_b", "set_4_a", "set_4_b",
    "set_5_a", "set_5_b", "source", "source_record_id",
    "source_index_record_id", "source_url", "source_index_url", "source_sha256",
]


def main() -> None:
    payload = SOURCE.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        records = list(csv.DictReader(stream, delimiter="\t"))
    if len(records) != 112:
        raise ValueError(f"Expected 112 results; found {len(records)}")
    ids = [r["source_record_id"] for r in records]
    if len(set(ids)) != 112:
        raise ValueError("Duplicate match-table record IDs")

    phases = Counter(r["phase"] for r in records)
    expected_phases = Counter({
        "intercontinental_round": 96, "final_round_pool": 12,
        "final_round_semifinal": 2, "final_round_bronze": 1,
        "final_round_final": 1,
    })
    if phases != expected_phases:
        raise ValueError(f"Phase census mismatch: {dict(phases)}")

    rows = []
    for record in records:
        match_id = record["source_record_id"].rsplit("-", 1)[-1]
        team_a, team_b = record["team_a_name"], record["team_b_name"]
        if team_a not in TEAM_CODES or team_b not in TEAM_CODES:
            raise ValueError(f"Unmapped team in {record['source_record_id']}")
        if team_a == team_b:
            raise ValueError(f"Self-match in {record['source_record_id']}")
        match_date = date.fromisoformat(record["match_date"])
        if match_date.year != 2001:
            raise ValueError(f"Out-of-season date: {record['match_date']}")
        sets_a, sets_b = (int(n) for n in record["result"].split("-"))
        if max(sets_a, sets_b) != 3 or min(sets_a, sets_b) not in (0, 1, 2):
            raise ValueError(f"Invalid best-of-five result: {record['source_record_id']}")
        row = {field: "" for field in FIELDS}
        row.update({
            "competition_key": "vnl",
            "competition_name": "FIVB Men's World League 2001",
            "season": "World League 2001",
            "gender": "M",
            "match_id": f"WL2001_{match_id}",
            "match_date": record["match_date"],
            "phase": record["phase"],
            "team_a_code": TEAM_CODES[team_a], "team_a_name": team_a,
            "team_b_code": TEAM_CODES[team_b], "team_b_name": team_b,
            "sets_a": str(sets_a), "sets_b": str(sets_b),
            "result_text": f"{sets_a}-{sets_b}",
            "source": "Newikis match table, cross-reconciled against archived OSSCG federation results",
            "source_record_id": record["source_record_id"],
            "source_index_record_id": record["source_record_id"],
            "source_url": ARCHIVE_URL,
            "source_index_url": TABLE_URL,
            "source_sha256": digest,
        })
        rows.append(row)

    def wins(items: list[dict[str, str]]) -> Counter:
        return Counter(r["team_a_name"] if int(r["sets_a"]) > int(r["sets_b"])
                       else r["team_b_name"] for r in items)

    initial_groups = [
        (range(1, 25), {"Italy": 9, "France": 8, "Spain": 5, "Argentina": 2}),
        (range(25, 49), {"Russia": 8, "Poland": 7, "Greece": 6, "Venezuela": 3}),
        (range(49, 73), {"Cuba": 10, "FR Yugoslavia": 10, "Japan": 3, "Portugal": 1}),
        (range(73, 97), {"Brazil": 11, "Netherlands": 7, "United States": 6, "Germany": 0}),
    ]
    for numbers, expected in initial_groups:
        subset = [r for i, r in enumerate(rows, 1) if i in numbers]
        if len(subset) != 24 or wins(subset) != Counter(expected):
            raise ValueError(f"Intercontinental standings mismatch: {dict(wins(subset))}")
    final_groups = [
        (range(97, 103), {"Brazil": 3, "FR Yugoslavia": 1, "France": 1, "Poland": 1}),
        (range(103, 109), {"Italy": 2, "Russia": 2, "Cuba": 2, "Netherlands": 0}),
    ]
    for numbers, expected in final_groups:
        subset = [r for i, r in enumerate(rows, 1) if i in numbers]
        if len(subset) != 6 or wins(subset) != Counter(expected):
            raise ValueError(f"Final-pool standings mismatch: {dict(wins(subset))}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Imported {len(rows)} results; phase census and six pool standings reconciled; "
          f"archived winner check documented; set-point fields excluded; source sha256={digest}")


if __name__ == "__main__":
    main()
