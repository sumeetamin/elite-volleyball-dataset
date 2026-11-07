"""Import and reconcile the archived UOL 2006/07 men's Superliga first phase."""
from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources" / "brazil_superliga_m_2006_07_uol_archive.tsv"
OUTPUT = ROOT / "data" / "silver" / "brazil_superliga_m_2006_07_uol.csv"
CONFLICTS = ROOT / "reports" / "brazil_superliga_m_2006_07_uol_conflicts.csv"
URL = "https://web.archive.org/web/20080709003311/http://esporte.uol.com.br/volei/superliga/masc_jogos0607.jhtm"
FIELDS = ("source", "source_match_id", "competition_key", "competition", "sex", "season",
          "phase", "round", "match_date", "home_team", "away_team", "home_sets",
          "away_sets", "status", "source_url", "source_sha256")
STANDINGS_WINS = {
    "Cimed": 27, "Telemig Celular/Minas": 26, "Ulbra/Uptime": 21,
    "Unisul/Nexxera": 18, "Banespa/São Bernardo": 17, "Sada/Betim": 16,
    "Fátima/UCS": 15, "Online/São Leopoldo": 14, "Vôlei Futuro": 13,
    "Shopping ABC/Santo André": 12, "Barão/Blumenau": 8,
    "São Caetano/Tamoyo": 7, "Ingá Alvares/Vitória": 7,
    "Bento Vôlei": 5, "Lupo/Náutico": 4,
}
ALIASES = {
    "Cimed": "Cimed", "Minas": "Telemig Celular/Minas", "Ulbra": "Ulbra/Uptime",
    "Unisul": "Unisul/Nexxera", "Banespa": "Banespa/São Bernardo",
    "Betim": "Sada/Betim", "UCS": "Fátima/UCS",
    "São Leopoldo": "Online/São Leopoldo", "São Leopolpo": "Online/São Leopoldo",
    "Vôlei Futuro": "Vôlei Futuro", "Santo André": "Shopping ABC/Santo André",
    "Blumenau": "Barão/Blumenau", "São Caetano": "São Caetano/Tamoyo",
    "Vitória": "Ingá Alvares/Vitória", "Bento": "Bento Vôlei", "Náutico": "Lupo/Náutico",
}
# In these two UOL rows, score-caption outcomes conflict with both the listed
# partial set scores and the final standings. Correct the match result from
# those two independent evidence fields; retain the original captions in bronze.
CORRECTIONS = {
    183: (2, 3, "source caption 3-2; set scores and standings support 2-3"),
    184: (3, 0, "source caption 0-3; set scores and standings support 3-0"),
}


def import_results() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    raw_bytes = SOURCE.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(source_rows) != 210:
        raise ValueError(f"Expected 210 first-phase rows, got {len(source_rows)}")

    pairs: Counter[tuple[str, str]] = Counter()
    directed: Counter[tuple[str, str]] = Counter()
    wins: Counter[str] = Counter()
    appearances: Counter[str] = Counter()
    per_round: Counter[tuple[str, str]] = Counter()
    output: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for row in source_rows:
        source_line = int(row["source_line"])
        phase, round_no = row["phase"], int(row["round"])
        home, away = row["home"], row["away"]
        if home not in STANDINGS_WINS or away not in STANDINGS_WINS or home == away:
            raise ValueError(f"Unknown or duplicate club: {row}")
        hs, ass = int(row["home_sets"]), int(row["away_sets"])
        listed_hs, listed_ass = int(row["listed_home_sets"]), int(row["listed_away_sets"])
        if max(hs, ass) != 3 or min(hs, ass) not in (0, 1, 2):
            raise ValueError(f"Invalid match result: {row}")
        if source_line in CORRECTIONS:
            expected = CORRECTIONS[source_line][:2]
            if (hs, ass) != expected:
                raise ValueError(f"Correction not applied at source line {source_line}")
            conflicts.append({
                "source_line": str(source_line), "kind": "match_result_corrected",
                "source_result": f"{listed_hs}-{listed_ass}", "normalized_result": f"{hs}-{ass}",
                "details": CORRECTIONS[source_line][2],
            })
        elif (hs, ass) != (listed_hs, listed_ass):
            raise ValueError(f"Unexpected result change at source line {source_line}")

        partials = [(int(a), int(b)) for a, b in re.findall(r"(\d+)[-/](\d+)", row["partial_scores"])]
        point_wins = (sum(a > b for a, b in partials), sum(b > a for a, b in partials))
        if len(partials) != hs + ass or point_wins != (hs, ass):
            conflicts.append({
                "source_line": str(source_line), "kind": "partial_score_conflict",
                "source_result": f"{listed_hs}-{listed_ass}", "normalized_result": f"{hs}-{ass}",
                "details": f"{row['partial_scores']} (set-point tally {point_wins[0]}-{point_wins[1]})",
            })

        played = date.fromisoformat(row["date"])
        expected_year = 2006 if played.month == 12 else 2007
        if played.year != expected_year:
            raise ValueError(f"Unexpected date-year mapping: {row['date']}")
        if phase not in {"first", "return"} or not 1 <= round_no <= 15:
            raise ValueError(f"Invalid phase/round: {row}")
        per_round[(phase, str(round_no))] += 1
        pair = tuple(sorted((home, away)))
        pairs[pair] += 1
        directed[(home, away)] += 1
        appearances[home] += 1
        appearances[away] += 1
        wins[home if hs == 3 else away] += 1

        identity = f"2006/07|M|{phase}|{round_no}|{home}|{away}"
        match_id = "uol-derived-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        if match_id in seen_ids:
            raise ValueError(f"Duplicate derived match identity: {identity}")
        seen_ids.add(match_id)
        output.append(dict(zip(FIELDS, (
            "UOL Esporte archived 2008 capture", match_id, "brazil_superliga",
            "Brazil Superliga", "M", "2006/07", "regular_season",
            f"{phase}_{round_no}", played.isoformat(), home, away, hs, ass,
            "completed", URL, digest,
        ))))

    if len(pairs) != 105 or set(pairs.values()) != {2}:
        raise ValueError("Expected all 105 unordered club pairings exactly twice")
    if len(directed) != 210 or set(directed.values()) != {1}:
        raise ValueError("Expected each home/away fixture exactly once")
    if set(per_round.values()) != {7} or len(per_round) != 30:
        raise ValueError("Expected 15 rounds of seven matches in each phase")
    if dict(appearances) != {team: 28 for team in STANDINGS_WINS}:
        raise ValueError(f"Not all 15 teams have 28 matches: {appearances}")
    if {team: wins[team] for team in STANDINGS_WINS} != STANDINGS_WINS:
        raise ValueError(f"Normalized match winners do not reconcile to standings: {wins}")
    if len(conflicts) != 10:
        raise ValueError(f"Expected two corrected outcomes and eight partial-score conflicts; got {len(conflicts)}")
    return output, conflicts


def main() -> None:
    rows, conflicts = import_results()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with CONFLICTS.open("w", encoding="utf-8", newline="") as stream:
        fields = ("source_line", "kind", "source_result", "normalized_result", "details")
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(conflicts)
    print(f"Imported {len(rows)} dated regular-season results; {len(conflicts)} documented source conflicts.")


if __name__ == "__main__":
    main()
