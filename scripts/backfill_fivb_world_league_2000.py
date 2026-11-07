"""Import and reconcile all 2000 men's World League matches.

The retained input stores each indexed match result alongside its corresponding
result in the archived OSSCG federation page. Dates are indexed from the
published match table. Set-point fields remain blank in normalized silver
because three point-score entries conflict across the two captures.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "sources/fivb_world_league_2000_osscg_wikipedia_crosscheck.tsv"
OUT_PATH = ROOT / "data/silver/fivb_legacy_world_league_2000_matches.csv"
ARCHIVE_URL = "https://web.archive.org/web/20080516194944/http://www.osscg.org.yu/volleyball_WL2005/2_historyWL_2000.asp"
DATE_INDEX_URL = "https://en.wikipedia.org/wiki/2000_FIVB_Volleyball_World_League"
FIELDS = ["competition_key", "competition_name", "season", "gender", "match_id",
          "match_date", "phase", "team_a_code", "team_a_name", "team_b_code",
          "team_b_name", "sets_a", "sets_b", "result_text", "set_1_a", "set_1_b",
          "set_2_a", "set_2_b", "set_3_a", "set_3_b", "set_4_a", "set_4_b",
          "set_5_a", "set_5_b", "source", "source_record_id",
          "source_index_record_id", "source_url", "source_index_url", "source_sha256"]


def winner(home: str, away: str, sets_home: int, sets_away: int) -> tuple[str, str]:
    return (home, away) if sets_home > sets_away else (away, home)


def normalize_points(team_a: str, team_b: str, sets_a: int, sets_b: int, points: str) -> str:
    winner_name = team_a if sets_a > sets_b else team_b
    normalized = []
    for token in points.split(";"):
        left, right = (int(v) for v in token.split(":"))
        normalized.append((left, right) if winner_name == team_a else (right, left))
    return ";".join(f"{left}:{right}" for left, right in normalized)


def main() -> None:
    payload = SOURCE_PATH.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    with SOURCE_PATH.open(encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f, delimiter="\t"))
    if len(source_rows) != 89:
        raise ValueError(f"Expected 89 match rows; found {len(source_rows)}")
    archive_ids = [r["archive_record_id"] for r in source_rows]
    if len(set(archive_ids)) != 89:
        raise ValueError("Duplicate archived source record IDs")
    if len({r["source_record_id"] for r in source_rows}) != 89:
        raise ValueError("Duplicate date-index record IDs")

    expected_phases = {"intercontinental_round": 72, "final_round_pool": 15,
                       "final_round_medal": 2}
    phases = Counter(r["phase"] for r in source_rows)
    if phases != Counter(expected_phases):
        raise ValueError(f"Phase census mismatch: {dict(phases)}")

    rows = []
    point_score_agreements = 0
    point_score_conflicts = []
    for i, src in enumerate(source_rows, start=1):
        a, b = int(src["sets_a"]), int(src["sets_b"])
        ah, aa = int(src["archive_sets_home"]), int(src["archive_sets_away"])
        if max(a, b) != 3 or min(a, b) not in (0, 1, 2):
            raise ValueError(f"Invalid indexed result: {src['source_record_id']}")
        if max(ah, aa) != 3 or min(ah, aa) not in (0, 1, 2):
            raise ValueError(f"Invalid archived result: {src['archive_record_id']}")
        if set((src["team_a_name"], src["team_b_name"])) != set((src["archive_home"], src["archive_away"])):
            raise ValueError(f"Team mismatch: {src['source_record_id']} / {src['archive_record_id']}")
        if winner(src["team_a_name"], src["team_b_name"], a, b) != winner(src["archive_home"], src["archive_away"], ah, aa):
            raise ValueError(f"Archived winner disagrees: {src['source_record_id']} / {src['archive_record_id']}")
        if int(src["wiki_table_line"]) != int(src["source_record_id"].rsplit("L", 1)[1]):
            raise ValueError(f"Table line/source ID mismatch: {src['source_record_id']}")

        row = {field: "" for field in FIELDS}
        row.update({
            "competition_key": "vnl",
            "competition_name": "FIVB Men's World League 2000",
            "season": "World League 2000",
            "gender": "M",
            "match_id": f"OSSCG_WL2000_{src['archive_record_id'].replace('-', '_')}",
            "match_date": src["match_date"],
            "phase": src["phase"],
            "team_a_code": src["team_a_code"],
            "team_a_name": src["team_a_name"],
            "team_b_code": src["team_b_code"],
            "team_b_name": src["team_b_name"],
            "sets_a": str(a), "sets_b": str(b), "result_text": f"{a}-{b}",
            "source": "OSSCG World League historical archive; dates indexed to published match table",
            "source_record_id": src["archive_record_id"],
            "source_index_record_id": src["source_record_id"],
            "source_url": ARCHIVE_URL,
            "source_index_url": DATE_INDEX_URL,
            "source_sha256": digest,
        })
        rows.append(row)
        # Score points are retained in the bronze capture but intentionally
        # omitted from silver; result-level verification remains reproducible.
        archive_points = normalize_points(src["archive_home"], src["archive_away"], ah, aa, src["archive_set_points"])
        wiki_points = normalize_points(src["team_a_name"], src["team_b_name"], a, b, src["wiki_set_points"])
        if archive_points == wiki_points:
            point_score_agreements += 1
        else:
            point_score_conflicts.append(src["source_record_id"])
    if point_score_agreements != 86 or len(point_score_conflicts) != 3:
        raise ValueError(f"Unexpected point-score reconciliation: {point_score_agreements} agree, {point_score_conflicts}")

    groups = {
        "A": (range(171, 195), {"FR Yugoslavia": 9, "Italy": 8, "Argentina": 4, "Canada": 3}),
        "B": (range(211, 235), {"Russia": 9, "France": 7, "Cuba": 5, "Netherlands": 3}),
        "C": (range(247, 271), {"United States": 10, "Brazil": 8, "Poland": 5, "Spain": 1}),
    }
    for name, (line_range, expected_wins) in groups.items():
        matches = [r for r in rows if int(r["source_index_record_id"].rsplit("L", 1)[1]) in line_range]
        wins = Counter(r["team_a_name"] if int(r["sets_a"]) > int(r["sets_b"])
                       else r["team_b_name"] for r in matches)
        if len(matches) != 24 or dict(wins) != expected_wins:
            raise ValueError(f"Initial pool {name} failed census/standings check: {len(matches)}, {dict(wins)}")
    final_matches = [r for r in rows
                     if 290 <= int(r["source_index_record_id"].rsplit("L", 1)[1]) <= 304]
    final_wins = Counter(r["team_a_name"] if int(r["sets_a"]) > int(r["sets_b"])
                         else r["team_b_name"] for r in final_matches)
    expected_final = {"Italy": 4, "Russia": 3, "FR Yugoslavia": 3,
                      "Brazil": 2, "Netherlands": 2, "United States": 1}
    if len(final_matches) != 15 or dict(final_wins) != expected_final:
        raise ValueError(f"Final-round standings check failed: {len(final_matches)}, {dict(final_wins)}")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Imported {len(rows)} results; 89/89 archived winners agree; "
          f"86 exact and 3 conflicting set-point records omitted; hash={digest}")


if __name__ == "__main__":
    main()

