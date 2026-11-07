"""Import and reconcile the archived 2004/05 women's Superliga first phase."""
import csv
import hashlib
import re
from collections import Counter
from datetime import date
from pathlib import Path
from import_brazil_w_2006_07_uol import FIELDS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/brazil_superliga_w_2004_05_uol_archive.tsv"
URL = "https://web.archive.org/web/20070610061147/http://esporte.uol.com.br/volei/superliga/fem_jogos0405.jhtm"
WINS = {"Osasco": 13, "Campos": 8, "MRV/Minas": 7, "Rexona": 16,
        "Brasil Telecom": 8, "Macaé": 1, "Pinheiros": 10,
        "São Caetano": 5, "Sesi": 4}

def main():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        source = list(csv.DictReader(f, delimiter="\t"))
    if len(source) != 72:
        raise ValueError(f"Expected 72 results; got {len(source)}")
    wins, pairs, output = Counter(), Counter(), []
    for row in source:
        m = re.fullmatch(r"(.*?) ([0-3]) x ([0-3]) (.*)", row["match"])
        if not m:
            raise ValueError(f"Unparsed match {row}")
        home, hs, away_s, away = m.groups()
        hs, away_s = int(hs), int(away_s)
        if home not in WINS or away not in WINS or max(hs, away_s) != 3 or min(hs, away_s) == 3:
            raise ValueError(f"Invalid teams or score: {row}")
        day, month = map(int, row["date"].split("/"))
        played = date(2004 if month == 11 else 2004 if month == 12 else 2005, month, day).isoformat()
        pairs[tuple(sorted((home, away)))] += 1
        wins[home if hs == 3 else away] += 1
        mid = hashlib.sha256(f"2004/05|F|{played}|{home}|{away}".encode()).hexdigest()[:20]
        output.append(dict(zip(FIELDS, ("UOL Esporte 2004/05 archive capture", "uol-derived-"+mid,
            "brazil_superliga", "Brazil Superliga", "F", "2004/05", "regular_season", "",
            played, home, away, hs, away_s, "completed", URL, digest))))
    if len(pairs) != 36 or set(pairs.values()) != {2} or dict(wins) != WINS:
        raise ValueError(f"Pairing/standings reconciliation failed: {len(pairs)} pairs, {dict(wins)}")
    out = ROOT / "data/silver/brazil_superliga_w_2004_05_uol.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, FIELDS); writer.writeheader(); writer.writerows(output)
    print(f"Imported {len(output)} regular-season results; all 36 pairings and standings reconcile")

if __name__ == "__main__": main()
