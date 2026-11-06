"""Compute auditable season coverage without inventing missing denominators."""
from pathlib import Path

import csv
from collections import Counter
import re


def build_coverage(inventory_path: Path, data_dir: Path) -> list[dict]:
    with inventory_path.open(encoding="utf-8-sig", newline="") as f:
        inventory = list(csv.DictReader(f))
    observed = {}
    cbv = data_dir / "silver" / "cbv_superliga_matches.csv"
    if cbv.exists():
        with cbv.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("phase") and row.get("phase") != "regular_season":
                    continue
                key = (row.get("competition_key", ""), row.get("season", ""), row.get("sex", ""))
                if row.get("match_status") == "completed":
                    observed[key] = observed.get(key, 0) + 1
    italy = data_dir / "silver" / "italy_superlega_m_2024_25.csv"
    if italy.exists():
        with italy.open(encoding="utf-8-sig", newline="") as f:
            observed[("italy_superlega", "2024/25", "M")] = sum(1 for _ in csv.DictReader(f))
    plusliga = data_dir / "silver" / "plusliga_m_2024_25.csv"
    if plusliga.exists():
        with plusliga.open(encoding="utf-8-sig", newline="") as f:
            observed[("plusliga", "2024/25", "M")] = sum(1 for _ in csv.DictReader(f))
    cev_path = data_dir / "silver" / "cev_champions_league_matches.csv"
    if cev_path.exists():
        by_season = Counter()
        with cev_path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                season = r.get("season_name", "")
                year = re.search(r"20\d{2}/\d{2}", season)
                sex = r.get("gender", "")
                if year:
                    by_season[("cev_cl", year.group(), sex)] += 1
        observed.update(by_season)
    # Sources whose published data are already represented in the repository.
    sources = [
        ("fivb_vis", data_dir / "silver" / "fivb_vis_matches.csv", "year"),
        ("volleyball_australia", data_dir / "silver" / "volleyball_australia_matches.csv", "year"),
    ]
    for comp, path, year_col in sources:
        if not path.exists():
            continue
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            col = year_col if year_col in headers else next((x for x in ("season_year", "match_year", "year") if x in headers), None)
            if not col:
                continue
            counts = Counter(str(r.get(col, ""))[:4] for r in reader)
        for year, count in counts.items():
            if year.isdigit(): observed[(comp, year, "*")] = count
    rows = []
    for rec in inventory:
        key = (str(rec["competition_key"]), str(rec["season"]), str(rec["sex"]))
        count = observed.get(key, observed.get((key[0], key[1], "*")))
        rate = (100 * count / float(rec["expected_matches"])) if count is not None and rec.get("expected_matches", "").strip() and float(rec["expected_matches"]) > 0 else ""
        threshold = float(rec.get("target_pct") or 80)
        rows.append({**rec, "observed_matches": count if count is not None else 0,
                     "observed_status": "records_found" if count else "no_records_found",
                     "coverage_pct": rate,
                     "target_pct": threshold,
                     "target_met": ("yes" if rate != "" and rate >= threshold else "no" if rate != "" else "unknown"),
                     "denominator_status": "verified" if rec.get("expected_matches", "").strip() else "unknown"})
    return rows
