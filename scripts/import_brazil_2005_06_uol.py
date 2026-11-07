"""Import UOL archived 2005/06 Superliga regular-season match results."""
import csv
import hashlib
import re
from collections import Counter
from datetime import date
from pathlib import Path
from import_brazil_w_2006_07_uol import FIELDS

ROOT = Path(__file__).resolve().parents[1]
WINS = {
    "F": {"Rexona": 16, "Osasco": 13, "Macaé": 11, "Pinheiros": 9,
          "São Caetano": 7, "Brasil Telecom": 6, "Minas": 4,
          "Flamengo": 4, "Suzano": 2},
    "M": {"Minas": 18, "Cimed": 16, "Banespa": 15, "Unisul": 14,
          "Bento": 14, "On Line": 13, "Campinas": 11, "Ulbra": 10,
          "UCS": 7, "Náutico": 6, "Santo André": 4, "São Caetano": 4},
}
URL = {
    "F": "https://web.archive.org/web/20070610061327/http://esporte.uol.com.br/volei/superliga/fem_jogos0506.jhtm",
    "M": "https://web.archive.org/web/20070610061238/http://esporte.uol.com.br/volei/superliga/masc_jogos0506.jhtm",
}

def import_season(sex):
    label = "w" if sex == "F" else "m"
    source = ROOT / f"sources/brazil_superliga_{label}_2005_06_uol_archive.tsv"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with source.open(encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream, delimiter="\t"))
    nteams = len(WINS[sex])
    expected = nteams * (nteams - 1)
    if len(raw) != expected:
        raise ValueError(f"Expected {expected} fixtures, found {len(raw)}")
    pairs, wins, out, conflicts = Counter(), Counter(), [], []
    for row in raw:
        m = re.fullmatch(r"(.*?) ([0-3]) x ([0-3]) (.*)", row["match"])
        if not m:
            raise ValueError(f"Unparsed result: {row}")
        home, hs, ass, away = m.groups()
        hs, ass = int(hs), int(ass)
        if home not in WINS[sex] or away not in WINS[sex] or home == away:
            raise ValueError(f"Unknown club: {row}")
        if max(hs, ass) != 3 or min(hs, ass) == 3:
            raise ValueError(f"Invalid set result: {row}")
        # This one published score conflicts with both the set-point winner
        # and the final standings. Those independent signals agree on 3–1.
        if sex == "M" and row["date"] == "08/02" and row["match"] == "On Line 1 x 3 Banespa":
            hs, ass = 3, 1
            conflicts.append("08/02 On Line–Banespa: corrected 1–3 to 3–1")
        partials = [(int(a), int(b)) for a,b in re.findall(r"(\d+)-(\d+)", row["partials"])]
        if len(partials) == hs + ass and sum(a > b for a,b in partials) != hs:
            conflicts.append(f"{row['date']} {row['match']}: set points conflict")
        month, day = (int(v) for v in row["date"].split("/")[::-1])
        year = 2005 if month == 12 else 2006
        played = date(year, month, day).isoformat()
        pairs[tuple(sorted((home, away)))] += 1
        wins[home if hs == 3 else away] += 1
        identity = f"2005/06|{sex}|{played}|{home}|{away}"
        match_id = "uol-derived-" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        out.append(dict(zip(FIELDS, ("UOL Esporte 2005/06 archive capture", match_id,
            "brazil_superliga", "Brazil Superliga", sex, "2005/06", "regular_season",
            "", played, home, away, hs, ass, "completed", URL[sex], digest))))
    if len(pairs) != nteams * (nteams - 1) // 2 or set(pairs.values()) != {2}:
        raise ValueError("Pair census does not match double round-robin")
    if {team: wins[team] for team in WINS[sex]} != WINS[sex]:
        raise ValueError(f"Scores disagree with archived standings: {wins}")
    return out, conflicts

if __name__ == "__main__":
    for sex in ("F", "M"):
        rows, conflicts = import_season(sex)
        output = ROOT / f"data/silver/brazil_superliga_{'w' if sex == 'F' else 'm'}_2005_06_uol.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"{sex}: {len(rows)} dated results; {len(conflicts)} source conflicts")
        for conflict in conflicts:
            print(" -", conflict)
