"""Import the complete 2002–03 men's World League archive from AIFVB.

The AIFVB historical PDF reproduces the full match tables, including match
numbers 1–112 for each edition. The PDF is downloaded to the ignored bronze
area; the derived match and coverage files are also ignored local data.
"""
from __future__ import annotations

import csv
import hashlib
import re
from datetime import date
from pathlib import Path

import pdfplumber
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://aifvb.fr/wp-content/uploads/2020/04/AIFVB-Histovolley_14-04-2020_vFD.pdf"
PDF_PATH = ROOT / "data/bronze/fivb_lineage/AIFVB-Histovolley_14-04-2020_vFD.pdf"
OUT_PATH = ROOT / "data/silver/fivb_legacy_world_league_2002_03_matches.csv"
COVERAGE_PATH = ROOT / "reports/fivb_legacy_aifvb_coverage.csv"
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
TEAM_NAMES = {
    "ARG": "Argentina", "BRA": "Brazil", "BUL": "Bulgaria", "CAN": "Canada",
    "CHN": "China", "CUB": "Cuba", "CZE": "Czech Republic", "ESP": "Spain", "FRA": "France",
    "FRY": "FR Yugoslavia", "GER": "Germany", "GRE": "Greece", "ITA": "Italy",
    "JPN": "Japan", "NED": "Netherlands", "POL": "Poland", "POR": "Portugal",
    "RUS": "Russia", "USA": "United States", "VEN": "Venezuela", "YUG": "Yugoslavia",
}
ROW = re.compile(
    r"^\s*(\d{1,3})\s+(\d{1,2})-([A-Z][a-z]{2})\s+([A-Z]{3})-([A-Z]{3})\s+([0-3])-([0-3])\s+(.*)$"
)
FIELDS = ["competition_key", "competition_name", "season", "gender", "match_id",
          "match_date", "phase", "team_a_code", "team_a_name", "team_b_code",
          "team_b_name", "sets_a", "sets_b", "result_text", "set_1_a", "set_1_b",
          "set_2_a", "set_2_b", "set_3_a", "set_3_b", "set_4_a", "set_4_b",
          "set_5_a", "set_5_b", "source", "source_record_id", "source_url", "source_sha256"]


def obtain_pdf() -> bytes:
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PDF_PATH.exists():
        response = requests.get(SOURCE_URL, timeout=90,
                                headers={"User-Agent": "elite-volleyball-dataset/1.0"})
        response.raise_for_status()
        PDF_PATH.write_bytes(response.content)
    return PDF_PATH.read_bytes()


def parse_season(year: int, pages: list[str], digest: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page_text in pages:
        for line in page_text.splitlines():
            match = ROW.match(line)
            if not match:
                continue
            no, day, month, code_a, code_b, sets_a, sets_b, tail = match.groups()
            n_sets = int(sets_a) + int(sets_b)
            pairs = re.findall(r"(?<!\d)(\d{1,2})-(\d{1,2})(?!\d)", tail)
            if int(sets_a) != 3 and int(sets_b) != 3:
                raise ValueError(f"Invalid match result {year}/{no}: {sets_a}-{sets_b}")
            if len(pairs) < n_sets:
                raise ValueError(f"Missing set scores in {year}/{no}: {tail}")
            month_no = MONTHS.get(month)
            if month_no is None:
                raise ValueError(f"Unrecognized month in {year}/{no}: {month}")
            game_date = date(year, month_no, int(day)).isoformat()
            points = pairs[:n_sets]
            if any(int(a) == int(b) for a, b in points):
                raise ValueError(f"Tied set points in {year}/{no}")
            if sum(int(a) > int(b) for a, b in points) != int(sets_a):
                raise ValueError(f"Set points conflict with result in {year}/{no}")
            if sum(int(b) > int(a) for a, b in points) != int(sets_b):
                raise ValueError(f"Set points conflict with result in {year}/{no}")
            code_a = code_a.upper()
            code_b = code_b.upper()
            if code_a not in TEAM_NAMES or code_b not in TEAM_NAMES:
                raise ValueError(f"Unknown AIFVB country code in {year}/{no}: {code_a}/{code_b}")
            padded = points + [("", "")] * (5 - len(points))
            row = {field: "" for field in FIELDS}
            row.update({
                "competition_key": "vnl",
                "competition_name": f"FIVB Men's World League {year}",
                "season": f"World League {year}", "gender": "M",
                "match_id": f"AIFVB_WL{year}_{int(no):03d}", "match_date": game_date,
                "phase": "intercontinental_round" if int(no) <= 96 else "final_round",
                "team_a_code": code_a, "team_a_name": team_name(year, code_a),
                "team_b_code": code_b, "team_b_name": team_name(year, code_b),
                "sets_a": sets_a, "sets_b": sets_b, "result_text": f"{sets_a}-{sets_b}",
                "source": "AIFVB Historical Volleyball Archive", "source_record_id": no,
                "source_url": SOURCE_URL, "source_sha256": digest,
            })
            for idx, (a, b) in enumerate(padded, start=1):
                row[f"set_{idx}_a"], row[f"set_{idx}_b"] = a, b
            rows.append(row)

    by_id = {int(row["source_record_id"]): row for row in rows}
    expected_ids = set(range(1, 113))
    if len(rows) != 112 or len(by_id) != 112 or set(by_id) != expected_ids:
        missing = sorted(expected_ids - set(by_id))
        duplicates = sorted(n for n in set(int(r["source_record_id"]) for r in rows)
                            if sum(int(x["source_record_id"]) == n for x in rows) > 1)
        raise RuntimeError(f"{year} census failed: rows={len(rows)}, missing={missing}, duplicates={duplicates}")
    return sorted(rows, key=lambda row: int(row["source_record_id"]))


def team_name(year: int, code: str) -> str:
    if code == "YUG":
        return "FR Yugoslavia" if year == 2002 else "Serbia and Montenegro"
    return TEAM_NAMES[code]


def write_coverage(rows: list[dict[str, str]]) -> None:
    fields = ["competition_key", "competition", "sex", "season", "phase", "expected_matches",
              "observed_matches", "dated_matches", "coverage_pct", "date_coverage_pct",
              "denominator_method", "source_url", "source_sha256", "target_met"]
    coverage = []
    for year in (2002, 2003):
        selected = [row for row in rows if row["season"] == f"World League {year}"]
        count = len(selected)
        coverage.append({
            "competition_key": "vnl", "competition": "FIVB international lineage", "sex": "M",
            "season": f"World League {year}", "phase": "all_official_tournament_matches",
            "expected_matches": "112", "observed_matches": str(count),
            "dated_matches": str(sum(bool(row["match_date"]) for row in selected)),
            "coverage_pct": f"{100 * count / 112:.2f}",
            "date_coverage_pct": f"{100 * sum(bool(row['match_date']) for row in selected) / 112:.2f}",
            "denominator_method": "AIFVB complete numbered match table 1–112; cross-checked against format count 96 intercontinental + 16 finals",
            "source_url": SOURCE_URL, "source_sha256": selected[0]["source_sha256"],
            "target_met": "yes" if count / 112 >= .8 else "no",
        })
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COVERAGE_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(coverage)


def update_ledgers(coverage_rows: list[dict[str, str]]) -> None:
    config_path = ROOT / "config/competition_seasons.csv"
    configs = list(csv.DictReader(config_path.open(encoding="utf-8-sig", newline="")))
    coverage_by_season = {row["season"]: row for row in coverage_rows}
    for row in configs:
        evidence = coverage_by_season.get(row["season"])
        if row["competition_key"] == "vnl" and row["sex"] == "M" and evidence:
            row["expected_matches"] = evidence["expected_matches"]
            row["official_schedule_url"] = SOURCE_URL
            row["notes"] = ("Complete 112-match results verified from AIFVB’s historical archive (match IDs 1–112; "
                            "96 intercontinental + 16 finals); AIFVB is a French federation-linked former-internationals association, "
                            "not FIVB VIS. See reports/fivb_legacy_aifvb_coverage.csv.")
    with config_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(configs[0]))
        writer.writeheader()
        writer.writerows(configs)

    ledger_path = ROOT / "reports/coverage_audit_current.csv"
    ledger = list(csv.DictReader(ledger_path.open(encoding="utf-8-sig", newline="")))
    for row in ledger:
        evidence = coverage_by_season.get(row["season"])
        if row["competition_key"] == "vnl" and row["sex"] == "M" and evidence:
            row["expected_matches"] = evidence["expected_matches"]
            row["official_schedule_url"] = SOURCE_URL
            row["notes"] = "Full 112-row AIFVB match table; match IDs 1–112 contiguous; 96 intercontinental + 16 finals."
            row["observed_matches"] = evidence["observed_matches"]
            row["observed_status"] = "complete_results"
            row["coverage_pct"] = evidence["coverage_pct"]
            row["target_met"] = evidence["target_met"]
            row["denominator_status"] = "verified_complete"
    with ledger_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ledger[0]))
        writer.writeheader()
        writer.writerows(ledger)


def main() -> None:
    payload = obtain_pdf()
    digest = hashlib.sha256(payload).hexdigest()
    with pdfplumber.open(PDF_PATH) as pdf:
        page_texts = [(page.extract_text() or "") for page in pdf.pages[168:177]]
    # Printed pages 168–171 contain World League 2002; 172–176 contain 2003.
    seasons = {
        2002: parse_season(2002, page_texts[:4], digest),
        2003: parse_season(2003, page_texts[4:], digest),
    }
    rows = [row for year in (2002, 2003) for row in seasons[year]]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    write_coverage(rows)
    # The shared ledger records observed coverage; preserve its established schema.
    ledger_rows = []
    for year in (2002, 2003):
        selection = seasons[year]
        ledger_rows.append({"season": f"World League {year}", "expected_matches": "112",
                            "observed_matches": str(len(selection)), "coverage_pct": "100.00",
                            "target_met": "yes"})
    update_ledgers(ledger_rows)
    print(f"Imported World League 2002-03: {len(rows)} matches; 112 each season.")


if __name__ == "__main__":
    main()
