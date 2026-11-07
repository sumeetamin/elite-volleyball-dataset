"""Import and reconcile UOL's archived 1999/2000 men's Superliga results."""
import csv
import hashlib
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from import_brazil_w_2006_07_uol import FIELDS

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/brazil_superliga_m_1999_2000_uol_archive.tsv"
OUTPUT = ROOT / "data/silver/brazil_superliga_m_1999_2000_uol.csv"
URL = "https://web.archive.org/web/20070610061220/http://esporte.uol.com.br/volei/superligamasc9900fase1.htm"
WINS = {"Telemig Cel/Minas": 19, "Unisul": 18, "Ulbra/Compaq": 18,
        "Banespa": 17, "Report/Nipomed": 16, "Telemig Cel/Unincor": 13,
        "São Paulo": 13, "Palmeiras/FO Cruz": 11, "Lupo/Náutico": 10,
        "Coop/Santo André": 8, "Bento Gonçalves": 6, "Barão/Hering": 5,
        "Intelbrás/São José": 2}
ALIASES = {"Tel. Cel/Unincor": "Telemig Cel/Unincor", "Telemig Cel/Un.": "Telemig Cel/Unincor",
           "Telemig Cel./Unincor": "Telemig Cel/Unincor", "Telemig Cel./Minas": "Telemig Cel/Minas",
           "Palmeiras/FOC": "Palmeiras/FO Cruz", "Palmeiras/O.Cruz": "Palmeiras/FO Cruz",
           "Intelbrás/SJ": "Intelbrás/São José", "Intelbrás/São Jose": "Intelbrás/São José",
           "Coop/Sto André": "Coop/Santo André", "COOP/Sto André": "Coop/Santo André",
           "Coop/Sto. André": "Coop/Santo André"}

def import_results():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream, delimiter="\t"))
    if len(raw) != 170:
        raise ValueError(f"Expected 170 published rows; got {len(raw)}")
    pairs, wins, maringa, out = Counter(), Counter(), 0, []
    for row in raw:
        match = re.fullmatch(r"(.*?) ([0-3]) x ([0-3]) (.*)", row["match"])
        if not match:
            raise ValueError(f"Unparsed score: {row}")
        home, hs, ass, away = match.groups()
        home, away = ALIASES.get(home, home), ALIASES.get(away, away)
        hs, ass = int(hs), int(ass)
        if max(hs, ass) != 3 or min(hs, ass) == 3 or home == away:
            raise ValueError(f"Invalid result: {row}")
        if "Maringá" in (home, away):
            maringa += 1
            continue  # Club withdrew; published results are not in final standings.
        if home not in WINS or away not in WINS:
            raise ValueError(f"Unknown club: {row}")
        date = datetime.strptime(row["date"], "%d/%m/%y").date().isoformat()
        pairs[tuple(sorted((home, away)))] += 1
        wins[home if hs == 3 else away] += 1
        identity = f"1999/2000|{date}|{home}|{away}"
        match_id = "uol-derived-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        out.append(dict(zip(FIELDS, ("UOL Esporte 1999/2000 archive capture", match_id,
            "brazil_superliga", "Brazil Superliga", "M", "1999/2000", "regular_season",
            "", date, home, away, hs, ass, "completed", URL, digest))))
    if maringa != 14 or len(out) != 156 or len(pairs) != 78 or set(pairs.values()) != {2}:
        raise ValueError("Maringá withdrawal or 13-club double round-robin does not reconcile")
    if {team: wins[team] for team in WINS} != WINS:
        raise ValueError(f"Results disagree with archived final standings: {wins}")
    return out

if __name__ == "__main__":
    rows = import_results()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Imported {len(rows)} dated regular-season outcomes")
