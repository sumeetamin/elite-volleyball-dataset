"""Import the complete 2004 men's World League result table.

The Wikipedia event page is used as a table index: every row links to its
official FIVB P2 match report, and the report filename supplies the FIVB
match number. The page's CC BY-SA attribution is retained in the output.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
INDEX_URL = "https://en.wikipedia.org/wiki/2004_FIVB_Volleyball_World_League"
PDF_DIR = ROOT / "data/bronze/fivb_lineage"
HTML_PATH = PDF_DIR / "wl2004_wikipedia.html"
OUT_PATH = ROOT / "data/silver/fivb_legacy_world_league_2004_matches.csv"
COVERAGE_PATH = ROOT / "reports/fivb_legacy_wikipedia_coverage.csv"
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
TEAM_CODES = {
    "Brazil": "BRA", "Greece": "GRE", "Spain": "ESP", "Portugal": "POR",
    "France": "FRA", "Bulgaria": "BUL", "Japan": "JPN", "Poland": "POL",
    "Italy": "ITA", "China": "CHN", "Serbia and Montenegro": "SCG", "Cuba": "CUB",
}
FIELDS = ["competition_key", "competition_name", "season", "gender", "match_id",
          "match_date", "phase", "team_a_code", "team_a_name", "team_b_code",
          "team_b_name", "sets_a", "sets_b", "result_text", "set_1_a", "set_1_b",
          "set_2_a", "set_2_b", "set_3_a", "set_3_b", "set_4_a", "set_4_b",
          "set_5_a", "set_5_b", "source", "source_record_id", "source_url",
          "source_index_url", "source_revision_id", "source_sha256", "source_license"]


def download_page() -> bytes:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    response = requests.get(INDEX_URL, timeout=60,
                            headers={"User-Agent": "elite-volleyball-dataset/1.0 (research archive)"})
    response.raise_for_status()
    HTML_PATH.write_bytes(response.content)
    return response.content


def pair(text: str, label: str) -> tuple[str, str]:
    values = re.findall(r"\d+", text)
    if len(values) != 2:
        raise ValueError(f"Invalid {label}: {text!r}")
    return values[0], values[1]


def main() -> None:
    payload = download_page()
    digest = hashlib.sha256(payload).hexdigest()
    html = payload.decode("utf-8", errors="replace")
    revision = re.search(r'"wgRevisionId"\s*:\s*(\d+)', html)
    if not revision:
        raise RuntimeError("Could not identify the Wikipedia page revision")
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    table_counts: list[int] = []

    for table in soup.find_all("table"):
        header_rows = table.find_all("tr")
        if not header_rows:
            continue
        headers = [cell.get_text(" ", strip=True) for cell in header_rows[0].find_all(["th", "td"])]
        if not {"Date", "Score", "Report"}.issubset(set(headers)):
            continue
        score_col = headers.index("Score")
        table_rows: list[dict[str, str]] = []
        for tr in header_rows[1:]:
            cells = tr.find_all("td")
            if len(cells) != len(headers):
                continue
            report_cell = cells[-1]
            report_anchor = next((a for a in report_cell.find_all("a")
                                  if a.get_text(strip=True) == "P2"), None)
            if report_anchor is None:
                continue
            report_url = report_anchor.get("href", "").replace("http://", "https://")
            official_number = re.search(r"match(\d+)\.pdf$", report_url)
            if not official_number:
                raise ValueError(f"Unexpected FIVB P2 report URL: {report_url}")
            team_a = cells[score_col - 1].get_text(" ", strip=True)
            score_a, score_b = pair(cells[score_col].get_text(" ", strip=True), "match score")
            team_b = cells[score_col + 1].get_text(" ", strip=True)
            if team_a not in TEAM_CODES or team_b not in TEAM_CODES:
                raise ValueError(f"Unknown team in Wikipedia table: {team_a!r}/{team_b!r}")
            points = [pair(cells[score_col + idx].get_text(" ", strip=True), "set score")
                      for idx in range(2, 7) if cells[score_col + idx].get_text(" ", strip=True)]
            if len(points) != int(score_a) + int(score_b):
                raise ValueError(f"Set-score count conflicts with {score_a}-{score_b} for {official_number.group(1)}")
            if sum(int(a) > int(b) for a, b in points) != int(score_a) or sum(int(b) > int(a) for a, b in points) != int(score_b):
                raise ValueError(f"Set scores conflict with match outcome for {official_number.group(1)}")
            date_text = cells[0].get_text(" ", strip=True).split()
            if len(date_text) != 2 or date_text[1] not in MONTHS:
                raise ValueError(f"Unknown date in result row: {date_text}")
            game_date = date(2004, MONTHS[date_text[1]], int(date_text[0])).isoformat()
            number = int(official_number.group(1))
            points.extend([("", "")] * (5 - len(points)))
            row = {field: "" for field in FIELDS}
            row.update({
                "competition_key": "vnl", "competition_name": "FIVB Men's World League 2004",
                "season": "World League 2004", "gender": "M",
                "match_id": f"FIVB_WL2004_{number:03d}", "match_date": game_date,
                "phase": "intercontinental_round" if number <= 72 else "final_round",
                "team_a_code": TEAM_CODES[team_a], "team_a_name": team_a,
                "team_b_code": TEAM_CODES[team_b], "team_b_name": team_b,
                "sets_a": score_a, "sets_b": score_b, "result_text": f"{score_a}-{score_b}",
                "source": "FIVB P2 match report (linked by Wikipedia)",
                "source_record_id": str(number), "source_url": report_url,
                "source_index_url": INDEX_URL, "source_revision_id": revision.group(1),
                "source_sha256": digest, "source_license": "CC BY-SA 4.0; attribution retained",
            })
            for idx, (a, b) in enumerate(points, start=1):
                row[f"set_{idx}_a"], row[f"set_{idx}_b"] = a, b
            table_rows.append(row)
        if table_rows:
            table_counts.append(len(table_rows))
            rows.extend(table_rows)

    ids = [int(row["source_record_id"]) for row in rows]
    if table_counts != [24, 24, 24, 2, 2, 1, 1]:
        raise RuntimeError(f"Unexpected result table counts: {table_counts}")
    if len(rows) != 78 or len(set(ids)) != 78 or set(ids) != set(range(1, 79)):
        raise RuntimeError(f"FIVB match-ID census failed: rows={len(rows)}, IDs={sorted(ids)}")
    rows.sort(key=lambda row: int(row["source_record_id"]))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader(); writer.writerows(rows)
    update_ledgers(rows, digest, revision.group(1))
    print("Imported World League 2004: 78 matches; official FIVB P2 IDs 1-78 contiguous.")


def update_ledgers(rows: list[dict[str, str]], digest: str, revision_id: str) -> None:
    source_note = ("Complete 78-match 2004 archive: 72 intercontinental + 6 finals; all official FIVB P2 IDs 1-78 "
                   f"contiguous. Wikipedia revision {revision_id} is the index; Volleybox independently lists 78 matches. "
                   "See reports/fivb_legacy_wikipedia_coverage.csv.")
    config_path = ROOT / "config/competition_seasons.csv"
    configs = list(csv.DictReader(config_path.open(encoding="utf-8-sig", newline="")))
    for row in configs:
        if row["competition_key"] == "vnl" and row["sex"] == "M" and row["season"] == "World League 2004":
            row["expected_matches"] = "78"
            row["official_schedule_url"] = INDEX_URL
            row["notes"] = source_note
    with config_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(configs[0])); writer.writeheader(); writer.writerows(configs)

    ledger_path = ROOT / "reports/coverage_audit_current.csv"
    ledger = list(csv.DictReader(ledger_path.open(encoding="utf-8-sig", newline="")))
    for row in ledger:
        if row["competition_key"] == "vnl" and row["sex"] == "M" and row["season"] == "World League 2004":
            row.update({"expected_matches": "78", "official_schedule_url": INDEX_URL,
                        "notes": source_note, "observed_matches": "78", "observed_status": "complete_results",
                        "coverage_pct": "100.00", "target_met": "yes", "denominator_status": "verified_complete"})
    with ledger_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ledger[0])); writer.writeheader(); writer.writerows(ledger)

    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COVERAGE_PATH.open("w", encoding="utf-8", newline="") as f:
        fields = ["competition_key", "competition", "sex", "season", "phase", "expected_matches",
                  "observed_matches", "dated_matches", "coverage_pct", "date_coverage_pct",
                  "denominator_method", "source_url", "source_sha256", "source_revision_id", "target_met"]
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        writer.writerow({"competition_key": "vnl", "competition": "FIVB international lineage", "sex": "M",
                         "season": "World League 2004", "phase": "all_official_tournament_matches",
                         "expected_matches": "78", "observed_matches": str(len(rows)),
                         "dated_matches": str(sum(bool(row["match_date"]) for row in rows)),
                         "coverage_pct": "100.00", "date_coverage_pct": "100.00",
                         "denominator_method": "FIVB P2 match-report IDs 1-78 contiguous; 72 intercontinental + 6 finals; Volleybox independently lists 78 matches",
                         "source_url": INDEX_URL, "source_sha256": digest,
                         "source_revision_id": revision_id, "target_met": "yes"})


if __name__ == "__main__":
    main()
