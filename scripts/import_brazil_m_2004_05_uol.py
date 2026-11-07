"""Import and reconcile the archived 2004/05 men's Superliga first phase."""
import csv
import hashlib
import re
from collections import Counter
from datetime import date
from pathlib import Path
from import_brazil_w_2006_07_uol import FIELDS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/brazil_superliga_m_2004_05_uol_archive.tsv"
URL = "https://web.archive.org/web/20070610060037/http://esporte.uol.com.br/volei/superliga/masc_jogos0405.jhtm"
# Abbreviated names used consistently by the archived fixture page; values
# match clubs in its final standings.
STANDINGS_WINS = {"Minas": 17, "Banespa": 15, "On Line": 14, "Suzano": 13,
                  "Ulbra": 12, "Bento": 10, "Unisul": 9, "Araraquara": 7,
                  "São Caetano": 6, "UCS": 5, "São José": 2}

def main():
    raw_bytes = SOURCE.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        source = list(csv.DictReader(f, delimiter="\t"))
    expected = len(STANDINGS_WINS) * (len(STANDINGS_WINS) - 1)
    if len(source) != expected:
        raise ValueError(f"Expected {expected} fixtures; found {len(source)}")
    wins, pairs, output, conflicts = Counter(), Counter(), [], []
    for row in source:
        m = re.fullmatch(r"(.*?) ([0-3]) x ([0-3]) (.*)", row["match"])
        if not m:
            raise ValueError(f"Unparsed fixture: {row}")
        home, hs, away_s, away = m.groups()
        hs, away_s = int(hs), int(away_s)
        if home not in STANDINGS_WINS or away not in STANDINGS_WINS or home == away:
            raise ValueError(f"Unknown or duplicate club: {row}")
        if max(hs, away_s) != 3 or min(hs, away_s) == 3:
            raise ValueError(f"Invalid best-of-five score: {row}")
        sets = [(int(a), int(b)) for a, b in re.findall(r"(\d+)-(\d+)", row["partials"])]
        if len(sets) != hs + away_s or sum(a > b for a, b in sets) != hs:
            conflicts.append(f"{row['date']} {row['match']}: partial sets conflict with listed set score")
        day, month = map(int, row["date"].split("/"))
        played = date(2004 if month in (11, 12) else 2005, month, day).isoformat()
        pairs[tuple(sorted((home, away)))] += 1
        wins[home if hs == 3 else away] += 1
        identity = f"2004/05|M|{played}|{home}|{away}"
        mid = hashlib.sha256(identity.encode()).hexdigest()[:20]
        output.append(dict(zip(FIELDS, ("UOL Esporte 2004/05 archive capture", "uol-derived-"+mid,
            "brazil_superliga", "Brazil Superliga", "M", "2004/05", "regular_season", "",
            played, home, away, hs, away_s, "completed", URL, digest))))
    if len(pairs) != 55 or set(pairs.values()) != {2}:
        raise ValueError(f"Expected all 55 pairings twice; found {len(pairs)} pairs")
    if dict(wins) != STANDINGS_WINS:
        raise ValueError(f"Result wins do not reconcile to archived standings: {dict(wins)}")
    out = ROOT / "data/silver/brazil_superliga_m_2004_05_uol.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, FIELDS); writer.writeheader(); writer.writerows(output)
    print(f"Imported {len(output)} results; all 55 pairings and standings reconcile; {len(conflicts)} partial-set conflicts")
    for conflict in conflicts:
        print(" - " + conflict)

if __name__ == "__main__": main()
