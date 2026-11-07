"""Import complete 2002–03 women's World Grand Prix results from AIFVB."""
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
OUT_PATH = ROOT / "data/silver/fivb_legacy_world_grand_prix_2002_03_matches.csv"
COVERAGE_PATH = ROOT / "reports/fivb_legacy_aifvb_wgp_coverage.csv"
MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
          "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
TEAM_NAMES = {
    "BRA": "Brazil", "CAN": "Canada", "CHN": "China", "CUB": "Cuba",
    "GER": "Germany", "ITA": "Italy", "JPN": "Japan", "KOR": "South Korea",
    "NED": "Netherlands", "RUS": "Russia", "THA": "Thailand", "USA": "United States",
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


def parse_edition(year: int, texts: list[str], expected: int, preliminary_last: int,
                  digest: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for page_text in texts:
        for line in page_text.splitlines():
            match = ROW.match(line)
            if not match:
                continue
            no, day, month, code_a, code_b, sets_a, sets_b, tail = match.groups()
            sets_a_num, sets_b_num = int(sets_a), int(sets_b)
            if sets_a_num != 3 and sets_b_num != 3:
                raise ValueError(f"Invalid match result {year}/{no}: {sets_a}-{sets_b}")
            n_sets = sets_a_num + sets_b_num
            pairs = re.findall(r"(?<!\d)(\d{1,2})-(\d{1,2})(?!\d)", tail)[:n_sets]
            if len(pairs) != n_sets:
                raise ValueError(f"Missing set scores in {year}/{no}: {tail}")
            if sum(int(a) > int(b) for a, b in pairs) != sets_a_num or sum(int(b) > int(a) for a, b in pairs) != sets_b_num:
                raise ValueError(f"Set points conflict with result in {year}/{no}")
            code_a, code_b = code_a.upper(), code_b.upper()
            if code_a not in TEAM_NAMES or code_b not in TEAM_NAMES:
                raise ValueError(f"Unknown AIFVB country code in {year}/{no}: {code_a}/{code_b}")
            month_no = MONTHS.get(month)
            if month_no is None:
                raise ValueError(f"Unrecognized month in {year}/{no}: {month}")
            padded = pairs + [("", "")] * (5 - len(pairs))
            row = {field: "" for field in FIELDS}
            row.update({
                "competition_key": "vnl", "competition_name": f"FIVB Women's World Grand Prix {year}",
                "season": f"World Grand Prix {year}", "gender": "F",
                "match_id": f"AIFVB_WGP{year}_{int(no):03d}",
                "match_date": date(year, month_no, int(day)).isoformat(),
                "phase": "preliminary_round" if int(no) <= preliminary_last else "final_round",
                "team_a_code": code_a, "team_a_name": TEAM_NAMES[code_a],
                "team_b_code": code_b, "team_b_name": TEAM_NAMES[code_b],
                "sets_a": sets_a, "sets_b": sets_b, "result_text": f"{sets_a}-{sets_b}",
                "source": "AIFVB Historical Volleyball Archive", "source_record_id": no,
                "source_url": SOURCE_URL, "source_sha256": digest,
            })
            for idx, (a, b) in enumerate(padded, start=1):
                row[f"set_{idx}_a"], row[f"set_{idx}_b"] = a, b
            rows.append(row)
    ids = [int(row["source_record_id"]) for row in rows]
    expected_ids = set(range(1, expected + 1))
    if len(rows) != expected or len(set(ids)) != expected or set(ids) != expected_ids:
        raise RuntimeError(f"{year} census failed: {len(rows)} rows, missing {sorted(expected_ids - set(ids))}")
    return sorted(rows, key=lambda row: int(row["source_record_id"]))


def update_ledgers(seasons: dict[int, list[dict[str, str]]], digest: str) -> None:
    config_path = ROOT / "config/competition_seasons.csv"
    configs = list(csv.DictReader(config_path.open(encoding="utf-8-sig", newline="")))
    ledger_path = ROOT / "reports/coverage_audit_current.csv"
    ledger = list(csv.DictReader(ledger_path.open(encoding="utf-8-sig", newline="")))
    report_fields = ["competition_key", "competition", "sex", "season", "phase", "expected_matches",
                     "observed_matches", "dated_matches", "coverage_pct", "date_coverage_pct",
                     "denominator_method", "source_url", "source_sha256", "target_met"]
    reports = []
    expected_by_year = {2002: (44, 36), 2003: (45, 30)}
    for year, (expected, preliminary_last) in expected_by_year.items():
        season = f"World Grand Prix {year}"
        rows = seasons[year]
        count = len(rows)
        reports.append({
            "competition_key": "vnl", "competition": "FIVB international lineage", "sex": "F",
            "season": season, "phase": "all_official_tournament_matches",
            "expected_matches": str(expected), "observed_matches": str(count),
            "dated_matches": str(sum(bool(row["match_date"]) for row in rows)),
            "coverage_pct": f"{100 * count / expected:.2f}",
            "date_coverage_pct": f"{100 * sum(bool(row['match_date']) for row in rows) / expected:.2f}",
            "denominator_method": f"AIFVB numbered tables 1-{expected} contiguous; format count {preliminary_last} preliminary + {expected - preliminary_last} finals",
            "source_url": SOURCE_URL, "source_sha256": digest, "target_met": "yes",
        })
        for row in configs:
            if row["competition_key"] == "vnl" and row["sex"] == "F" and row["season"] == season:
                row["expected_matches"] = str(expected)
                row["official_schedule_url"] = SOURCE_URL
                row["notes"] = (f"Complete {expected}-match results verified from AIFVB's historical archive "
                                f"(match IDs 1-{expected}; {preliminary_last} preliminary + {expected - preliminary_last} finals); "
                                "AIFVB is a French federation-linked former-internationals association, not FIVB VIS. "
                                "See reports/fivb_legacy_aifvb_wgp_coverage.csv.")
        for row in ledger:
            if row["competition_key"] == "vnl" and row["sex"] == "F" and row["season"] == season:
                row.update({"expected_matches": str(expected), "official_schedule_url": SOURCE_URL,
                            "notes": f"Full {expected}-row AIFVB result table; match IDs 1-{expected} contiguous.",
                            "observed_matches": str(count), "observed_status": "complete_results",
                            "coverage_pct": "100.00", "target_met": "yes",
                            "denominator_status": "verified_complete"})
    with config_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(configs[0])); writer.writeheader(); writer.writerows(configs)
    with ledger_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(ledger[0])); writer.writeheader(); writer.writerows(ledger)
    with COVERAGE_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=report_fields); writer.writeheader(); writer.writerows(reports)


def main() -> None:
    payload = obtain_pdf()
    digest = hashlib.sha256(payload).hexdigest()
    with pdfplumber.open(PDF_PATH) as pdf:
        texts = [(page.extract_text() or "") for page in pdf.pages[197:201]]
    # PDF indices 198-199 are WGP 2002; indices 200-201 contain WGP 2003.
    seasons = {
        2002: parse_edition(2002, texts[:2], expected=44, preliminary_last=36, digest=digest),
        2003: parse_edition(2003, texts[2:], expected=45, preliminary_last=30, digest=digest),
    }
    rows = [row for year in (2002, 2003) for row in seasons[year]]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    update_ledgers(seasons, digest)
    print(f"Imported World Grand Prix 2002-03: {len(rows)} matches; 44 in 2002 and 45 in 2003.")


if __name__ == "__main__":
    main()
