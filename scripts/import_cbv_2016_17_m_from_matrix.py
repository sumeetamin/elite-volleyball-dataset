"""Recover CBV 2016/17 men's regular-season results from fixture IDs + results matrix.

Dates, home/away teams, and fixture numbers come from CBV's official schedule
PDF. Final set scores come from a pinned local capture of the season results
matrix; the entire matrix is reconciled against the published final W/L table.
"""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

import pdfplumber
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE_URL = "https://wp.cbv.com.br/wp-content/uploads/2023/09/n.o.-179-4-179-cbv-tabela-oficial-superliga-masculina-2016-2017.pdf"
PAGE_TITLE = "Superliga_Brasileira_de_Voleibol_Masculino_de_2016%E2%80%9317_-_S%C3%A9rie_A"
RESULT_URL = "https://api.wikimedia.org/core/v1/wikipedia/pt/page/" + PAGE_TITLE + "/html"
PDF = ROOT / "data/bronze/cbv_2016_17_m_official_schedule.pdf"
HTML = ROOT / "data/bronze/cbv_2016_17_m_results_matrix.html"
OUT = ROOT / "data/silver/cbv_superliga_2016_17_m.csv"
REPORT = ROOT / "reports/cbv_2016_17_m_matrix_coverage.csv"
PROVENANCE = ROOT / "reports/cbv_2016_17_m_provenance.md"
FIELDS = ["source", "source_match_id", "competition", "season", "sex", "competition_key",
          "phase", "round", "match_date", "home_team", "away_team", "home_sets", "away_sets",
          "match_status", "source_url", "source_sha256", "date_source_url", "date_source_sha256",
          "source_match_number"]

TEAM_ALIASES = {
    "BVL": ("BENTO VOLEI",), "CAM": ("VOLEI BRASIL KIRIN",),
    "CAN": ("LEBES/GEDORE/CANOAS",), "TAU": ("FUNVIC/TAUBATE",),
    "MRG": ("COPEL TELECOM/ MARING", "COPEL TELECOM/MARING"),
    "MIN": ("MINAS TENIS CLUBE",), "MOC": ("MONTES CLAROS VOLEI",),
    "CAR": ("CARAMURU/CASTRO",), "CRU": ("SADA CRUZEIRO VOLEI",),
    "SES": ("SESI-SP",), "UJF": ("JF VOLEI", "FJ VOLEI"),
    "SBV": ("SAO BERNARDO VOLEI",),
}
STANDINGS_ALIAS = {
    "SADA CRUZEIRO VOLEI": "CRU", "FUNVIC/TAUBATE": "TAU", "SESI-SP": "SES",
    "VOLEI RENATA": "CAM", "MONTES CLAROS VOLEI": "MOC",
    "MINAS TENIS CLUBE": "MIN", "JUIZ DE FORA VOLEI": "UJF",
    "LEBES/GEDORE/CANOAS": "CAN", "BENTO VOLEI/ISABELA": "BVL",
    "COPEL TELECOM/MARINGA VOLEI": "MRG", "SAO BERNARDO VOLEI": "SBV",
    "MV SELMER/CARAMURU/CASTRO": "CAR",
}


def ascii_fold(value: str) -> str:
    value = value.replace("�", "")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()).strip().upper()


def fetch_sources() -> tuple[bytes, bytes]:
    PDF.parent.mkdir(parents=True, exist_ok=True)
    if not PDF.exists():
        r = requests.get(SCHEDULE_URL, timeout=60, headers={"User-Agent": "elite-volleyball-dataset/1.0"})
        r.raise_for_status(); PDF.write_bytes(r.content)
    if HTML.exists():
        html = HTML.read_bytes()
    else:
        r = requests.get(RESULT_URL, timeout=60, headers={"User-Agent": "elite-volleyball-dataset/1.0 (research)"})
        r.raise_for_status()
        html = r.content
        HTML.write_bytes(html)
    return PDF.read_bytes(), html


def parse_matrix(html: bytes) -> tuple[dict[str, dict[str, tuple[int, int]]], dict[str, str], dict[str, tuple[int, int, int]]]:
    soup = BeautifulSoup(html, "html.parser")
    matrix_table = None
    standings_table = None
    for table in soup.select("table.wikitable"):
        trs = table.select("tr")
        if not trs:
            continue
        first = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"], recursive=False)]
        if len(first) == 14 and "BVL" in first and "UJF" in first:
            matrix_table = table
        if len(trs) >= 13:
            header_rows = [[c.get_text(" ", strip=True) for c in row.find_all(["th", "td"], recursive=False)] for row in trs[:2]]
            if len(header_rows) == 2 and {"Pos", "Equipe", "Pts", "T", "V", "D"}.issubset(header_rows[1]):
                standings_table = table
    if matrix_table is None or standings_table is None:
        raise ValueError("Could not locate score matrix and final standings tables")
    headers = [c.get_text(" ", strip=True) for c in matrix_table.select("tr")[0].find_all(["th", "td"], recursive=False)]
    codes = headers[1:-1]
    matrix: dict[str, dict[str, tuple[int, int]]] = {}
    names: dict[str, str] = {}
    for tr in matrix_table.select("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"], recursive=False)]
        if len(cells) != 14:
            raise ValueError(f"Malformed score matrix row: {cells}")
        code = cells[0].split()[0]
        names[code] = cells[0][len(code):].strip()
        matrix[code] = {}
        for opponent, result in zip(codes, cells[1:-1]):
            if not result:
                continue
            score = re.fullmatch(r"(\d+)\s*[-–—−�]\s*(\d+)", result)
            if not score:
                raise ValueError(f"Invalid score cell {code} vs {opponent}: {result!r}")
            a, b = int(score.group(1)), int(score.group(2))
            if max(a, b) != 3 or min(a, b) not in {0, 1, 2}:
                raise ValueError(f"Impossible volleyball result {code} {result} {opponent}")
            matrix[code][opponent] = (a, b)
    if set(matrix) != set(codes) or sum(map(len, matrix.values())) != 132:
        raise ValueError(f"Expected 12 teams and 132 directed results; got {len(matrix)} teams, {sum(map(len,matrix.values()))} results")
    standings: dict[str, tuple[int, int, int]] = {}
    for tr in standings_table.select("tr")[2:14]:
        c = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"], recursive=False)]
        if len(c) < 6:
            continue
        name = ascii_fold(c[1])
        if name not in STANDINGS_ALIAS:
            raise ValueError(f"Unmapped standings team {c[1]!r}")
        standings[STANDINGS_ALIAS[name]] = (int(c[3]), int(c[4]), int(c[5]))
    if set(standings) != set(matrix):
        raise ValueError(f"Standings/matrix teams differ: {set(standings)} vs {set(matrix)}")
    # The published matrix has UJF vs TAU as 2-3, conflicting with both
    # teams' final W/L totals. Contemporary reports agree Juiz de Fora won 3-2
    # on 11 Mar 2017 (fixture 131); retain that independently verified result.
    if matrix.get("UJF", {}).get("TAU") == (2, 3):
        matrix["UJF"]["TAU"] = (3, 2)
    for team in matrix:
        home_w = sum(a == 3 for a, b in matrix[team].values())
        home_l = sum(b == 3 for a, b in matrix[team].values())
        away_w = sum(matrix[other][team][1] == 3 for other in matrix if other != team)
        away_l = sum(matrix[other][team][0] == 3 for other in matrix if other != team)
        gp, wins, losses = standings[team]
        if (home_w + away_w, home_l + away_l) != (wins, losses) or gp != wins + losses:
            raise ValueError(f"Matrix does not reconcile to standings for {team}: matrix {(home_w+away_w,home_l+away_l)}, standings {(gp,wins,losses)}")
    return matrix, names, standings


def parse_schedule(pdf_bytes: bytes) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with pdfplumber.open(PDF) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for raw in table:
                    if len(raw) < 10 or not raw[0] or not raw[0].strip().isdigit():
                        continue
                    number = int(raw[0].strip())
                    date_text = re.sub(r"\s+", " ", raw[1] or "").strip()
                    # pdfplumber can merge the participant-list headings into
                    # match 120's team cells; the actual team is the last line.
                    home = re.sub(r"\s+", " ", (raw[5] or "").splitlines()[-1]).strip()
                    away = re.sub(r"\s+", " ", (raw[9] or "").splitlines()[-1]).strip()
                    dm = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_text)
                    match_date = ""
                    if dm:
                        yr = int(dm.group(3)); yr += 2000 if yr < 100 else 0
                        match_date = datetime(yr, int(dm.group(2)), int(dm.group(1))).date().isoformat()
                    if number == 84 and "CRUZEI" in home and "RAMURU" in away:
                        # Table extraction interleaves the team names with the
                        # participant header; restore the names/date visible in
                        # the official PDF row (28 Jan 2017).
                        home, away, match_date = "SADA CRUZEIRO VOLEI", "CARAMURU/CASTRO", "2017-01-28"
                    rows.append({"number": str(number), "raw_date": date_text, "match_date": match_date,
                                 "home_team": home, "away_team": away})
    # One PDF glyph-layout glitch reads official match 98 as "8". Recover only
    # from the known missing/duplicate sequence and its February 2017 date.
    counts = Counter(int(r["number"]) for r in rows)
    missing = set(range(1, 133)) - set(counts)
    duplicates = {n for n, c in counts.items() if c > 1}
    if missing == {98} and duplicates == {8}:
        for row in rows:
            if row["number"] == "8" and row["raw_date"].startswith("11/02/17"):
                row["number"] = "98"
                break
    ids = [int(r["number"]) for r in rows]
    if len(rows) != 132 or set(ids) != set(range(1, 133)) or len(set(ids)) != 132:
        raise ValueError(f"Official schedule ID check failed: {len(rows)} rows, missing {set(range(1,133))-set(ids)}")
    return rows


def code_for_team(team: str) -> str:
    name = ascii_fold(team)
    matches = [code for code, aliases in TEAM_ALIASES.items() if any(ascii_fold(alias) in name for alias in aliases)]
    if len(matches) != 1:
        raise ValueError(f"Cannot uniquely map CBV schedule team {team!r}: {matches}")
    return matches[0]


def main() -> None:
    pdf_bytes, html = fetch_sources()
    matrix, team_names, standings = parse_matrix(html)
    schedule = parse_schedule(pdf_bytes)
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    html_hash = hashlib.sha256(html).hexdigest()
    records = []
    pair_counts: Counter[tuple[str, str]] = Counter()
    for fixture in schedule:
        home_code, away_code = code_for_team(fixture["home_team"]), code_for_team(fixture["away_team"])
        result = matrix[home_code].get(away_code)
        if result is None:
            raise ValueError(f"No matrix result for scheduled home/away pair {home_code}-{away_code}")
        hs, aw = result
        pair_counts[(home_code, away_code)] += 1
        records.append({"source": "CBV official fixture schedule + Wikimedia result matrix; standings-reconciled",
                        "source_match_id": f"CBV2016_17_M_{int(fixture['number']):03d}",
                        "competition": "Brazil Superliga", "season": "2016/17", "sex": "M",
                        "competition_key": "brazil_superliga", "phase": "regular_season",
                        "round": f"round_{(int(fixture['number'])-1)//6+1:02d}",
                        "match_date": fixture["match_date"], "home_team": fixture["home_team"],
                        "away_team": fixture["away_team"], "home_sets": str(hs), "away_sets": str(aw),
                        "match_status": "completed", "source_url": RESULT_URL, "source_sha256": html_hash,
                        "date_source_url": SCHEDULE_URL, "date_source_sha256": pdf_hash,
                        "source_match_number": fixture["number"]})
    if len(records) != 132 or len({r['source_match_id'] for r in records}) != 132:
        raise ValueError("Expected 132 unique regular-season fixtures")
    if len({code_for_team(r['home_team']) for r in schedule}) != 12:
        raise ValueError("Expected exactly 12 participating teams")
    # Confirm the official schedule contains each directed home/away pairing once.
    if set(pair_counts.values()) != {1} or len(pair_counts) != 132:
        raise ValueError("Unexpected duplicate/missing directed pair in official fixture schedule")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(sorted(records, key=lambda r:int(r['source_match_number'])))
    dated = sum(bool(r['match_date']) for r in records)
    coverage = {"competition_key":"brazil_superliga", "competition":"Brazil Superliga", "sex":"M",
                "season":"2016/17", "phase":"regular_season", "participating_teams":12,
                "games_per_team":22, "expected_matches":132, "observed_matches":132,
                "dated_matches":dated, "coverage_pct":100.0, "date_coverage_pct":round(100*dated/132,2),
                "target_pct":80, "target_met":"yes", "denominator_method":"CBV official schedule IDs 1–132; 12-team double round-robin; score matrix fully reconciled against final 22-game win/loss standings",
                "schedule_source_url":SCHEDULE_URL, "schedule_source_sha256":pdf_hash,
                "result_source_url":RESULT_URL, "result_source_sha256":html_hash}
    with REPORT.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(coverage)); w.writeheader(); w.writerow(coverage)
    PROVENANCE.write_text(
        "# CBV Superliga men 2016/17 regular-season results\n\n"
        f"Official fixtures and schedule numbers: [{SCHEDULE_URL}]({SCHEDULE_URL}); results matrix: [{RESULT_URL}]({RESULT_URL}).\n\n"
        "The CBV schedule lists 132 unique regular-season fixture IDs with dates and home/away teams. The season results matrix contains 12 team rows × 11 opponent scores (132 directed home/away results). Each matrix score was matched to the scheduled home/away pair. Matrix-derived team wins and losses reconcile to all 12 published final standings records (22 GP each). The source exposes set-wins only, not set point scores.\n\n"
        "Correction: the matrix cell UJF–TAU reads 2–3 but conflicts with both final standings totals. Contemporary coverage of the 11 March 2017 match reports Juiz de Fora winning 3–2: [ge.globo.com](https://ge.globo.com/mg/zona-da-mata-centro-oeste/volei/noticia/2017/03/jf-volei-leva-melhor-sobre-taubate-na-previa-das-quartas-da-superliga.html), [Tribuna de Minas](https://tribunademinas.com.br/noticias/esportes/13-03-2017/jf-volei-encara-funvic-taubate-nas-quartas-de-final.html). The importer corrects this cell and records the correction here.\n\n"
        f"PDF SHA-256: `{pdf_hash}`. Result-matrix HTML SHA-256: `{html_hash}`. Imported **132/132 (100%)** results; exact-date coverage **{dated}/132 ({100*dated/132:.2f}%)**.\n",
        encoding="utf-8")
    print(f"2016/17 men: {len(records)}/132 results, {dated}/132 dated; all matrix W/L reconciled; PDF sha256={pdf_hash}; matrix sha256={html_hash}")


if __name__ == "__main__":
    main()
