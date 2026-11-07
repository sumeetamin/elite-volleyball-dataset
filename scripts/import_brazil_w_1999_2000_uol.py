"""Import UOL's archived 1999/2000 women's Superliga first-phase scores."""
import csv
import hashlib
from collections import Counter
from datetime import datetime
from pathlib import Path
from import_brazil_w_2006_07_uol import FIELDS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/brazil_superliga_w_1999_2000_uol_archive.tsv"
OUTPUT = ROOT / "data/silver/brazil_superliga_w_1999_2000_uol.csv"
URL = "https://web.archive.org/web/20070610055851/http://esporte.uol.com.br/volei/superligafem9900fase1.htm"
ALIASES = {"Fla./Petrobras": "Flamengo/Petrobras", "Flamengo/Petr.": "Flamengo/Petrobras",
           "Petrobras/FO": "Petrobras/F.Olímpica", "Petrobras/FO.": "Petrobras/F.Olímpica",
           "Petrobras/F.O.": "Petrobras/F.Olímpica"}
WINS = {"Rexona": 18, "BCN/Osasco": 18, "MRV/Minas": 16,
        "Blue Life/Pinheiros": 14, "Flamengo/Petrobras": 13,
        "Grêmio Londrina": 9, "São Caetano": 8, "Petrobras/Macaé": 7,
        "Recreativa": 4, "Fox/Cascavel": 3, "Petrobras/F.Olímpica": 0}


def import_results():
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream, delimiter="\t"))
    if len(source_rows) != 110:
        raise ValueError(f"Expected 110 fixtures, got {len(source_rows)}")
    rounds = Counter((r["phase"], r["round"]) for r in source_rows)
    if rounds != Counter({(p, str(n)): 5 for p in ("first", "return") for n in range(1, 12)}):
        raise ValueError("Expected eleven five-match rounds in each phase")
    meetings, directed, wins = Counter(), Counter(), Counter()
    output = []
    for row in source_rows:
        home, away = (ALIASES.get(row[s], row[s]) for s in ("home", "away"))
        if home not in WINS or away not in WINS or home == away:
            raise ValueError(f"Unknown team in {row}")
        hs, ass = int(row["home_sets"]), int(row["away_sets"])
        if (hs == 3) == (ass == 3) or min(hs, ass) < 0 or max(hs, ass) != 3:
            raise ValueError(f"Invalid score in {row}")
        match_date = datetime.strptime(row["date"], "%d/%m/%y").date().isoformat()
        identity = f"1999/2000|{row['phase']}|{row['round']}|{home}|{away}"
        match_id = "uol-derived-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        meetings[tuple(sorted((home, away)))] += 1
        directed[(home, away)] += 1
        wins[home if hs == 3 else away] += 1
        output.append(dict(zip(FIELDS, ("UOL Esporte 1999/2000 archive capture",
            match_id, "brazil_superliga", "Brazil Superliga", "F", "1999/2000",
            "regular_season", f"{row['phase']}_{row['round']}", match_date,
            home, away, hs, ass, "completed", URL, digest))))
    # The archive lists Fox/Cascavel as home against Petrobras/Macaé in both
    # legs. Retain its published ordering; pair counts and standings still
    # reconcile, but home venue needs independent verification for that pair.
    if len(meetings) != 55 or set(meetings.values()) != {2} or len(directed) != 109:
        raise ValueError("Expected 55 pairs twice and one documented home-order exception")
    if {team: wins[team] for team in WINS} != WINS:
        raise ValueError(f"Winners disagree with final standings: {wins}")
    return output


if __name__ == "__main__":
    rows = import_results()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Imported {len(rows)} dated regular-season outcomes")
