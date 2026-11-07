"""Normalize the complete UOL archive capture for Brazil Superliga women 2008/09."""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sources/brazil_superliga_w_2008_09_uol_archive.tsv"
OUTPUT = ROOT / "data/silver/brazil_superliga_w_2008_09_uol.csv"
URLS = {
    "t1": "https://www.uol.com.br/esporte/volei/2008/superliga/jogos01_fem.jhtm",
    "t2": "https://www.uol.com.br/esporte/volei/2008/superliga/jogos02_fem.jhtm",
    "t3": "https://www.uol.com.br/esporte/volei/2008/superliga/jogos03_fem.jhtm",
    "t4": "https://www.uol.com.br/esporte/volei/2008/superliga/jogos04_fem.jhtm",
    "playoffs": "https://www.uol.com.br/esporte/volei/2008/superliga/finais_fem.jhtm",
}
TEAMS = {"Rexona", "Finasa", "Brasil Telecom", "São Caetano", "Banespa", "Mackenzie", "Vôlei Futuro", "Pomerode", "Minas", "Pinheiros", "Praia Clube", "Sport"}
EXPECTED = {"t1": 31, "t2": 37, "t3": 37, "t4": 31, "playoffs": 16}
FIELDS = ("source", "source_match_id", "competition_key", "competition", "sex", "season", "phase", "round", "match_date", "home_team", "away_team", "home_sets", "away_sets", "status", "source_url", "source_sha256")


def main() -> None:
    payload = SOURCE.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream, delimiter="\t"))
    census = Counter(row["stage"] for row in source_rows)
    if census != Counter(EXPECTED):
        raise ValueError(f"Stage census mismatch: {census}; expected {EXPECTED}")
    rounds = Counter((row["stage"], row["round"]) for row in source_rows)
    for stage, round_count, per_round in (("t1", 5, 6), ("t2", 6, 6), ("t3", 6, 6), ("t4", 5, 6)):
        expected = Counter({(stage, str(round_no)): per_round for round_no in range(1, round_count + 1)})
        observed = Counter({key: value for key, value in rounds.items() if key[0] == stage and key[1] != "final"})
        if observed != expected or rounds[(stage, "final")] != 1:
            raise ValueError(f"Tournament round census mismatch for {stage}: {observed}")
    playoff_counts = Counter(row["round"].split("_")[0] for row in source_rows if row["stage"] == "playoffs")
    if playoff_counts != Counter({"quarterfinal": 8, "semifinal": 6, "bronze": 1, "championship": 1}):
        raise ValueError(f"Playoff census mismatch: {playoff_counts}")

    output, seen = [], set()
    wins_by_stage: dict[str, Counter[str]] = {stage: Counter() for stage in ("t1", "t2", "t3", "t4")}
    for item in source_rows:
        stage, rnd = item["stage"], item["round"]
        match_date = date.fromisoformat(item["date"]).isoformat()
        home, away = item["home"].strip(), item["away"].strip()
        hs, aws = int(item["home_sets"]), int(item["away_sets"])
        if home not in TEAMS or away not in TEAMS or home == away:
            raise ValueError(f"Unknown or repeated team: {item}")
        if max(hs, aws) != 3 or min(hs, aws) not in (0, 1, 2):
            raise ValueError(f"Invalid completed result: {item}")
        identity = f"2008/09|{stage}|{rnd}|{match_date}|{home}|{away}"
        if identity in seen:
            raise ValueError(f"Duplicate fixture: {identity}")
        seen.add(identity)
        if stage != "playoffs" and rnd != "final":
            wins_by_stage[stage][home if hs == 3 else away] += 1
        phase = "playoffs" if stage == "playoffs" else ("tournament_final" if rnd == "final" else "regular_season")
        output.append(dict(zip(FIELDS, (
            "UOL Esporte 2008/09 archive", "uol-derived-" + hashlib.sha256(identity.encode()).hexdigest()[:20],
            "brazil_superliga", "Brazil Superliga", "F", "2008/09", phase,
            f"{stage}_{rnd}", match_date, home, away, hs, aws, "completed", URLS[stage], digest,
        ))))
    # Match outcomes must agree with contemporaneous UOL group-table win totals.
    expected_wins = {
        "t1": {"Rexona": 5, "Brasil Telecom": 4, "São Caetano": 3, "Mackenzie": 2, "Vôlei Futuro": 1, "Pomerode": 0, "Minas": 4, "Finasa": 3, "Pinheiros": 3, "Praia Clube": 3, "Banespa": 2, "Sport": 0},
        "t2": {"Rexona": 5, "São Caetano": 4, "Brasil Telecom": 4, "Mackenzie": 3, "Vôlei Futuro": 2, "Pomerode": 0, "Finasa": 6, "Pinheiros": 5, "Banespa": 3, "Sport": 2, "Praia Clube": 1, "Minas": 1},
        "t3": {"Rexona": 5, "São Caetano": 5, "Brasil Telecom": 4, "Mackenzie": 4, "Pomerode": 2, "Vôlei Futuro": 2, "Finasa": 6, "Pinheiros": 4, "Praia Clube": 2, "Sport": 1, "Minas": 1, "Banespa": 0},
        "t4": {"Rexona": 5, "São Caetano": 4, "Mackenzie": 2, "Vôlei Futuro": 2, "Brasil Telecom": 2, "Pomerode": 0, "Finasa": 5, "Pinheiros": 4, "Banespa": 3, "Praia Clube": 2, "Minas": 1, "Sport": 0},
    }
    for stage, expected in expected_wins.items():
        observed = {team: wins_by_stage[stage][team] for team in TEAMS}
        if observed != expected:
            raise ValueError(f"{stage} group wins fail standings reconciliation: {observed}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(f"Imported {len(output)} unique completed results; stage census={dict(census)}; SHA-256={digest}")


if __name__ == "__main__":
    main()
