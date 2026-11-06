"""Compute auditable season coverage without inventing missing denominators."""
from pathlib import Path

import csv
from collections import Counter
import re


def _canonical_cev_season(label: str) -> str | None:
    """Normalize both 2000/01 and 2000/2001 labels from CEV archive pages."""
    match = re.search(r"\b(20\d{2})\s*/\s*(?:20)?(\d{2})\b", label)
    if not match:
        return None
    return f"{match.group(1)}/{match.group(2)}"


def _fivb_vnl_key(row: dict[str, str]) -> tuple[str, str, str] | None:
    """Map an FIVB VIS row to its annual World League/Grand Prix/VNL ledger key.

    Qualification events and test-only placeholder events are deliberately
    excluded. Explicit years in the event title must agree with edition_year;
    this prevents date-query duplicates or qualification events from leaking
    into a different annual competition edition.
    """
    title = (row.get("competition_name") or "").strip()
    folded = title.casefold()
    if not title or re.search(r"\b(qualification|qualifying|qualifier|test only)\b", folded):
        return None
    sex = {"W": "F", "F": "F", "M": "M"}.get((row.get("gender") or "").upper())
    if not sex:
        return None
    vnl_name = re.search(r"volleyball\s+nations\s+league|\bvnl\b", folded)
    if sex == "M" and not (re.search(r"world league", folded) or vnl_name):
        return None
    if sex == "F" and not (re.search(r"world grand prix", folded) or vnl_name):
        return None
    year_text = (row.get("edition_year") or "").strip()
    year_match = re.search(r"\b(20\d{2})\b", year_text) or re.search(r"\b(20\d{2})\b", title)
    if not year_match:
        return None
    year = int(year_match.group(1))
    title_year = re.search(r"\b(20\d{2})\b", title)
    if title_year and int(title_year.group(1)) != year:
        return None
    if year >= 2018:
        season = f"VNL {year}"
    else:
        season = f"{'World League' if sex == 'M' else 'World Grand Prix'} {year}"
    return "vnl", season, sex


def _valid_completed_outcome(row: dict[str, str]) -> bool:
    """Require a finished provider state and a valid best-of-five set result."""
    status = (row.get("status") or "").strip().casefold()
    if status not in {"closed", "result is official", "finished", "corrected"}:
        return False
    try:
        sets_a, sets_b = int(row.get("sets_a", "")), int(row.get("sets_b", ""))
    except (TypeError, ValueError):
        return False
    return max(sets_a, sets_b) == 3 and min(sets_a, sets_b) in {0, 1, 2}


def build_coverage(inventory_path: Path, data_dir: Path) -> list[dict]:
    with inventory_path.open(encoding="utf-8-sig", newline="") as f:
        inventory = list(csv.DictReader(f))
    observed = {}
    available_sources = set()
    cbv = data_dir / "silver" / "cbv_superliga_matches.csv"
    if cbv.exists():
        available_sources.add("brazil_superliga")
        with cbv.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("phase") and row.get("phase") != "regular_season":
                    continue
                key = (row.get("competition_key", ""), row.get("season", ""), row.get("sex", ""))
                if row.get("match_status") == "completed":
                    observed[key] = observed.get(key, 0) + 1
    italy = data_dir / "silver" / "italy_superlega_m_2024_25.csv"
    if italy.exists():
        available_sources.add("italy_superlega")
        with italy.open(encoding="utf-8-sig", newline="") as f:
            observed[("italy_superlega", "2024/25", "M")] = sum(1 for _ in csv.DictReader(f))
    plusliga = data_dir / "silver" / "plusliga_m_2024_25.csv"
    if plusliga.exists():
        available_sources.add("plusliga")
        with plusliga.open(encoding="utf-8-sig", newline="") as f:
            observed[("plusliga", "2024/25", "M")] = sum(1 for _ in csv.DictReader(f))
    cev_path = data_dir / "silver" / "cev_champions_league_matches.csv"
    if cev_path.exists():
        available_sources.add("cev_cl")
        by_season = Counter()
        with cev_path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                season = r.get("season_name", "")
                canonical_season = _canonical_cev_season(season)
                sex = {"W": "F", "Women": "F"}.get(r.get("gender", ""), r.get("gender", ""))
                try:
                    sets_a, sets_b = int(r.get("sets_a", "")), int(r.get("sets_b", ""))
                except (TypeError, ValueError):
                    continue
                if canonical_season and max(sets_a, sets_b) == 3 and min(sets_a, sets_b) in (0, 1, 2):
                    by_season[("cev_cl", canonical_season, sex)] += 1
        observed.update(by_season)
    # Sources whose published data are already represented in the repository.
    sources = [
        ("fivb_vis", data_dir / "silver" / "fivb_vis_matches.csv", "year"),
        ("volleyball_australia", data_dir / "silver" / "volleyball_australia_matches.csv", "year"),
    ]
    for comp, path, year_col in sources:
        if not path.exists():
            continue
        available_sources.add(comp)
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if comp == "fivb_vis":
                available_sources.add("vnl")
                seen = set()
                for record in reader:
                    key = _fivb_vnl_key(record)
                    if not key or not _valid_completed_outcome(record):
                        continue
                    identity = (key, record.get("match_id") or record.get("source_record_id") or "")
                    if not identity[1] or identity in seen:
                        continue
                    seen.add(identity)
                    observed[key] = observed.get(key, 0) + 1
                continue
            col = year_col if year_col in headers else next((x for x in ("season_year", "match_year", "year") if x in headers), None)
            if not col:
                continue
            counts = Counter(str(r.get(col, ""))[:4] for r in reader)
        for year, count in counts.items():
            if year.isdigit(): observed[(comp, year, "*")] = count
    rows = []
    for rec in inventory:
        key = (str(rec["competition_key"]), str(rec["season"]), str(rec["sex"]))
        season_status = (rec.get("season_status") or "").strip().casefold()
        if not season_status and re.search(r"\bseason_status=cancelled\b", rec.get("notes", ""), re.IGNORECASE):
            season_status = "cancelled"
        # A primary-source cancellation is a verified disposition, not a
        # missing archive or a season with a zero-match denominator.
        if season_status == "cancelled":
            rows.append({**rec, "observed_matches": "",
                         "observed_status": "cancelled",
                         "coverage_pct": "",
                         "target_pct": float(rec.get("target_pct") or 80),
                         "target_met": "not_applicable",
                         "denominator_status": "not_applicable"})
            continue
        count = observed.get(key, observed.get((key[0], key[1], "*")))
        collected = key[0] in available_sources
        archive_marker = re.search(r"\bfivb_archive_status=(not_listed|listed_unmanaged)\b",
                                   rec.get("notes", ""), re.IGNORECASE)
        archive_observation = ({"not_listed": "not_listed_in_official_vis_index",
                               "listed_unmanaged": "listed_but_unmanaged_in_vis"}
                              .get(archive_marker.group(1).casefold()) if archive_marker else "")
        rate = (100 * count / float(rec["expected_matches"])) if collected and count is not None and rec.get("expected_matches", "").strip() and float(rec["expected_matches"]) > 0 else ""
        threshold = float(rec.get("target_pct") or 80)
        rows.append({**rec, "observed_matches": count if collected and count is not None else "",
                     "observed_status": ("records_found" if count else archive_observation or "zero_records_in_available_file") if collected else (archive_observation or "source_not_collected"),
                     "coverage_pct": rate,
                     "target_pct": threshold,
                     "target_met": ("yes" if rate != "" and rate >= threshold else "no" if rate != "" else "unknown"),
                     "denominator_status": "verified" if rec.get("expected_matches", "").strip() else "unknown"})
    return rows
