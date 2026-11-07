"""Import the archived UOL 2006/07 women's Superliga regular-season results.

The contemporary match page has 14 rounds x four matches. Its scoreboard is
reconciled to the final standings. Two set-point strings contradict its set
scores; set points are deliberately not imported.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources" / "brazil_superliga_w_2006_07_uol_archive.tsv"
OUTPUT = ROOT / "data" / "silver" / "brazil_superliga_w_2006_07_uol.csv"
ARCHIVE_URL = "https://web.archive.org/web/20080727032525/http%3A//esporte.uol.com.br/volei/superliga/fem_jogos0607.jhtm"
FIELDS = ("source", "source_match_id", "competition_key", "competition", "sex", "season", "phase", "round", "match_date", "home_team", "away_team", "home_sets", "away_sets", "status", "source_url", "source_sha256")
STANDINGS_WINS = {"Rexona": 13, "Osasco": 12, "Minas": 8, "São Caetano": 8,
                  "Macaé": 7, "Pinheiros": 5, "Brasil Telecom": 2, "Vôlei Futuro": 1}


def import_results() -> list[dict[str, str]]:
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(source_rows) != 56:
        raise ValueError(f"Expected 56 results, got {len(source_rows)}")
    rounds = Counter((r["phase"], r["round"]) for r in source_rows)
    if rounds != Counter({(phase, str(n)): 4 for phase in ("first", "return") for n in range(1, 8)}):
        raise ValueError("Expected seven four-match rounds in each phase")
    teams = set(STANDINGS_WINS)
    pairings = Counter()
    directed = Counter()
    wins = Counter()
    output = []
    for row in source_rows:
        home, away = row["home"].strip(), row["away"].strip()
        if home not in teams or away not in teams or home == away:
            raise ValueError(f"Unknown or duplicate team in {row}")
        hs, ass = int(row["home_sets"]), int(row["away_sets"])
        if (hs == 3) == (ass == 3) or min(hs, ass) < 0 or max(hs, ass) != 3:
            raise ValueError(f"Invalid set score in {row}")
        month, day = (int(x) for x in row["date"].split("/")[::-1])
        year = 2006 if month == 12 else 2007
        match_date = date(year, month, day).isoformat()
        identity = f"2006/07|{row['phase']}|{row['round']}|{home}|{away}"
        derived_id = "uol-derived-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        pairings[tuple(sorted((home, away)))] += 1
        directed[(home, away)] += 1
        wins[home if hs == 3 else away] += 1
        output.append(dict(zip(FIELDS, (
            "UOL Esporte archived 2008 capture", derived_id, "brazil_superliga", "Brazil Superliga",
            "F", "2006/07", "regular_season", f"{row['phase']}_{row['round']}",
            match_date, home, away, hs, ass, "completed", ARCHIVE_URL, digest,
        ))))
    if len(pairings) != 28 or set(pairings.values()) != {2} or len(directed) != 56:
        raise ValueError("Expected every pair once in each home direction")
    if dict(wins) != STANDINGS_WINS:
        raise ValueError(f"Result wins do not match archived final standings: {wins}")
    return output


def main() -> None:
    rows = import_results()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Imported {len(rows)} dated regular-season outcomes to {OUTPUT}")


if __name__ == "__main__":
    main()
