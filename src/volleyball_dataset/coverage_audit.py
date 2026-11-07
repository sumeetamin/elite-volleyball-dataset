"""Compute auditable season coverage without inventing missing denominators."""
from pathlib import Path

import csv
from collections import Counter
import re


def _canonical_cev_season(label: str) -> str | None:
    """Normalize both 2000/01 and 2000/2001 labels from CEV archive pages."""
    match = re.search(r"\b(20\d{2})\s*/\s*(?:20)?(\d{2})\b", label)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    # CEV titles from 2011 onward often name the final calendar year only.
    # Its 2012 competition, for example, began in October 2011.
    edition = re.search(r"\b(20\d{2})\s+CEV\b|\bCEV\b.*\b(20\d{2})\b", label, re.IGNORECASE)
    if edition and "champions league" in label.casefold():
        end_year = int(edition.group(1) or edition.group(2))
        return f"{end_year - 1}/{end_year % 100:02d}"
    return None


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
    italy_denominators = {}
    italy_report = data_dir.parent / "reports" / "italy_superlega_historical_coverage_2026-11-06.csv"
    if italy_report.exists():
        with italy_report.open(encoding="utf-8-sig", newline="") as f:
            italy_denominators = {r["season"]: r for r in csv.DictReader(f)}
    italy_women_denominators = {}
    women_report = data_dir / "coverage_italy_women_historical.csv"
    if women_report.exists():
        with women_report.open(encoding="utf-8-sig", newline="") as f:
            italy_women_denominators = {r["season"]: r for r in csv.DictReader(f)}
    cev_denominators = {}
    cev_report = data_dir / "local" / "cev_coverage_by_edition_2000_2026_27.csv"
    if cev_report.exists():
        with cev_report.open(encoding="utf-8-sig", newline="") as f:
            for report_row in csv.DictReader(f):
                season = _canonical_cev_season(report_row.get("season_name", ""))
                sex = {"M": "M", "W": "F", "F": "F"}.get(report_row.get("gender", ""))
                # Require the full official season LegList and every discovered
                # page to parse; omit the ongoing 2026/27 edition.
                if (season and season != "2026/27" and sex
                        and report_row.get("all_pages_ok", "").casefold() == "true"
                        and int(report_row.get("complete_leglist_page_count") or 0) >= 1):
                    cev_denominators[(season, sex)] = report_row
    plusliga_denominators = {}
    for plusliga_report in (data_dir.parent / "reports").glob("plusliga_m_*coverage*.csv"):
        with plusliga_report.open(encoding="utf-8-sig", newline="") as f:
            plusliga_denominators.update({(r["season"], r["phase"]): r for r in csv.DictReader(f)})
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
    historical_italy = data_dir / "silver" / "italy_superlega_matches_2000_2026.csv"
    if historical_italy.exists():
        available_sources.add("italy_superlega")
        counts = Counter()
        with historical_italy.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    home, away = int(row.get("home_sets", "")), int(row.get("away_sets", ""))
                except (TypeError, ValueError):
                    continue
                if row.get("status") == "completed" and max(home, away) == 3 and min(home, away) in (0, 1, 2):
                    counts[("italy_superlega", row.get("season", ""), "M")] += 1
        observed.update(counts)
    italy_women = data_dir / "silver" / "italy_serie_a1_women_matches.csv"
    if italy_women.exists():
        available_sources.add("italy_serie_a1_women")
        counts = Counter()
        seen_women = set()
        with italy_women.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                identity = (row.get("season", ""), row.get("source_match_id", ""))
                if not identity[1] or identity in seen_women:
                    continue
                seen_women.add(identity)
                try:
                    home, away = int(row.get("home_sets", "")), int(row.get("away_sets", ""))
                except (TypeError, ValueError):
                    continue
                if row.get("status") == "completed" and max(home, away) == 3 and min(home, away) in (0, 1, 2):
                    counts[("italy_serie_a1_women", row.get("season", ""), "F")] += 1
        observed.update(counts)
    plusliga = data_dir / "silver" / "plusliga_m_2024_25.csv"
    if plusliga.exists():
        available_sources.add("plusliga")
        with plusliga.open(encoding="utf-8-sig", newline="") as f:
            observed[("plusliga", "2024/25", "M")] = sum(1 for _ in csv.DictReader(f))
    historical_plusliga = data_dir / "silver" / "plusliga_m_2000_01_head_to_head.csv"
    if historical_plusliga.exists():
        available_sources.add("plusliga")
        counts = Counter()
        seen = set()
        with historical_plusliga.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("phase") != "regular_season":
                    continue
                identity = (row.get("season", ""), row.get("source_match_id", ""))
                if not identity[1] or identity in seen:
                    continue
                seen.add(identity)
                try:
                    home, away = int(row.get("home_sets", "")), int(row.get("away_sets", ""))
                except (TypeError, ValueError):
                    continue
                if row.get("status") == "completed" and max(home, away) == 3 and min(home, away) in (0, 1, 2):
                    counts[("plusliga", identity[0], "M")] += 1
        observed.update(counts)
    plusliga_by_season = Counter()
    for historical_plusliga in (data_dir / "silver").glob("plusliga_m_*_matches.csv"):
        available_sources.add("plusliga")
        counts = Counter()
        seen = set()
        with historical_plusliga.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("phase") != "regular_season":
                    continue
                identity = (row.get("season", ""), row.get("source_match_id", ""))
                if not identity[1] or identity in seen:
                    continue
                seen.add(identity)
                try:
                    home, away = int(row.get("home_sets", "")), int(row.get("away_sets", ""))
                except (TypeError, ValueError):
                    continue
                if row.get("status") == "completed" and max(home, away) == 3 and min(home, away) in (0, 1, 2):
                    counts[("plusliga", identity[0], "M")] += 1
        plusliga_by_season.update(counts)
    observed.update(plusliga_by_season)
    # Independently imported season files use stable per-season filenames.
    # Include them alongside the combined legacy tables so the refreshed
    # coverage ledger reflects every published local silver dataset.
    silver = data_dir / "silver"
    recent_results = Counter()
    recent_seen = set()
    for pattern, competition, sex in (
        ("tauron_liga_w_*_matches.csv", "tauron_liga", "F"),
        ("cbv_superliga_2016_17_*.csv", "brazil_superliga", None),
        ("brazil_superliga_w_2006_07_uol.csv", "brazil_superliga", "F"),
        ("brazil_superliga_w_1999_2000_uol.csv", "brazil_superliga", "F"),
        ("brazil_superliga_m_1999_2000_uol.csv", "brazil_superliga", "M"),
        ("brazil_superliga_w_2005_06_uol.csv", "brazil_superliga", "F"),
        ("brazil_superliga_m_2005_06_uol.csv", "brazil_superliga", "M"),
        ("brazil_superliga_w_2004_05_uol.csv", "brazil_superliga", "F"),
        ("brazil_superliga_m_2004_05_uol.csv", "brazil_superliga", "M"),
        ("brazil_superliga_m_2006_07_uol.csv", "brazil_superliga", "M"),
        ("brazil_superliga_w_2008_09_uol.csv", "brazil_superliga", "F"),
        ("fivb_legacy_world_league_2000_matches.csv", "vnl", "M"),
        ("fivb_legacy_world_league_2001_matches.csv", "vnl", "M"),
        ("fivb_legacy_world_league_2002_03_matches.csv", "vnl", "M"),
        ("fivb_legacy_world_grand_prix_2002_03_matches.csv", "vnl", "F"),
        ("fivb_lineage_matches.csv", "vnl", None),
    ):
        for path in silver.glob(pattern):
            if competition == "tauron_liga":
                available_sources.add(competition)
            elif competition == "brazil_superliga":
                available_sources.add(competition)
            else:
                available_sources.add(competition)
            with path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    row_sex = sex or row.get("sex", row.get("gender", ""))
                    row_sex = {"W": "F", "Women": "F", "Men": "M"}.get(row_sex, row_sex)
                    if competition == "tauron_liga":
                        row_sex = "F"
                    season = row.get("season", "")
                    if competition == "vnl" and path.name == "fivb_lineage_matches.csv":
                        lineage_key = _fivb_vnl_key({
                            "competition_name": row.get("competition_name", ""),
                            "gender": row_sex,
                            "edition_year": row.get("edition_year", ""),
                        })
                        if not lineage_key:
                            continue
                        _, season, row_sex = lineage_key
                    if not season:
                        year = row.get("year", row.get("edition_year", ""))
                        season = (f"World League {year}" if competition == "vnl" and row_sex == "M" and year
                                  else f"World Grand Prix {year}" if competition == "vnl" and row_sex == "F" and year
                                  else "")
                    try:
                        a = int(row.get("home_sets", row.get("sets_a", "")))
                        b = int(row.get("away_sets", row.get("sets_b", "")))
                    except (TypeError, ValueError):
                        continue
                    status = (row.get("status") or row.get("match_status") or "completed").casefold()
                    if status in {"completed", "finished", "closed", "result is official", "corrected"} and max(a, b) == 3 and min(a, b) in (0, 1, 2):
                        key = (competition, season, row_sex)
                        identity = row.get("source_match_id") or row.get("match_id") or row.get("source_record_id") or ""
                        fingerprint = (key, identity or (row.get("match_date", row.get("scheduled_at_utc", "")),
                                                          row.get("home_team", row.get("team_a_name", "")),
                                                          row.get("away_team", row.get("team_b_name", "")), a, b))
                        if fingerprint in recent_seen:
                            continue
                        recent_seen.add(fingerprint)
                        recent_results[key] += 1
    # The older result APIs may also contain these same rows. Season-specific
    # source IDs are the canonical count for these matched editions.
    observed.update(recent_results)
    # Per-season canonical tables supersede any older combined table for the
    # same slice. This also avoids including playoffs where the season table
    # explicitly carries phase=regular_season.
    canonical_files = list(silver.glob("tauron_liga_w_*_matches.csv"))
    canonical_files += list(silver.glob("cbv_superliga_2016_17_*.csv"))
    canonical_files += list(silver.glob("brazil_superliga_w_2006_07_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_w_1999_2000_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_m_1999_2000_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_*_2005_06_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_w_2004_05_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_m_2004_05_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_m_2006_07_uol.csv"))
    canonical_files += list(silver.glob("brazil_superliga_w_2008_09_uol.csv"))
    for path in canonical_files:
        with path.open(encoding="utf-8-sig", newline="") as f:
            first = next(csv.DictReader(f), None)
        if not first:
            continue
        key = (first.get("competition_key", ""), first.get("season", ""), first.get("sex", ""))
        count = recent_results.get(key)
        if count is not None:
            observed[key] = count
    cev_path = data_dir / "local" / "cev_champions_league_matches_2000_2026_27.csv"
    if not cev_path.exists():
        cev_path = data_dir / "silver" / "cev_champions_league_matches.csv"
    if cev_path.exists():
        available_sources.add("cev_cl")
        by_season = Counter()
        seen_cev = set()
        with cev_path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                season = r.get("season_name", "")
                canonical_season = _canonical_cev_season(season)
                sex = {"W": "F", "Women": "F"}.get(r.get("gender", ""), r.get("gender", ""))
                if (r.get("match_status") or "").casefold() in {"cancelled", "canceled", "abandoned", "not_scheduled", "postponed"}:
                    continue
                match_id = r.get("match_id") or r.get("source_record_id") or ""
                identity = (canonical_season, sex, match_id)
                if not match_id or identity in seen_cev:
                    continue
                try:
                    sets_a, sets_b = int(r.get("sets_a", "")), int(r.get("sets_b", ""))
                except (TypeError, ValueError):
                    continue
                if canonical_season and max(sets_a, sets_b) == 3 and min(sets_a, sets_b) in (0, 1, 2):
                    by_season[("cev_cl", canonical_season, sex)] += 1
                    seen_cev.add(identity)
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
    # Backfill older FIVB lineages from their dedicated archived tables.
    for filename in ("fivb_legacy_world_league_2002_03_matches.csv",
                     "fivb_legacy_world_grand_prix_2002_03_matches.csv",
                     "fivb_legacy_world_league_2004_matches.csv"):
        path = silver / filename
        if not path.exists():
            continue
        available_sources.add("vnl")
        with path.open(encoding="utf-8-sig", newline="") as f:
            counts = Counter((r.get("season", ""), {"W": "F"}.get(r.get("gender", ""), r.get("gender", "")))
                             for r in csv.DictReader(f)
                             if _valid_completed_outcome({"status": "finished", "sets_a": r.get("sets_a", ""), "sets_b": r.get("sets_b", "")}))
        for (season, sex), count in counts.items():
            observed[("vnl", season, sex)] = count
    rows = []
    canonical_recent_keys = set(recent_results)
    canonical_recent_keys.update(("vnl", season, sex) for season, sex in (
        ("World League 2000", "M"),
        ("World League 2002", "M"), ("World League 2003", "M"),
        ("World Grand Prix 2002", "F"), ("World Grand Prix 2003", "F"),
        ("World League 2004", "M"),
    ))
    for rec in inventory:
        if rec["competition_key"] == "italy_superlega" and not rec.get("expected_matches"):
            audit = italy_denominators.get(rec["season"])
            if audit and audit["season_status"] != "in_progress":
                rec["expected_matches"] = audit["expected_matches_double_round_robin"]
                rec["official_schedule_url"] = audit["source_urls"].split(";")[0]
                rec["notes"] = (rec.get("notes", "") + " Official historical denominator and source hashes: reports/italy_superlega_historical_coverage_2026-11-06.csv").strip()
        if rec["competition_key"] == "italy_serie_a1_women" and not rec.get("expected_matches"):
            audit = italy_women_denominators.get(rec["season"])
            if audit:
                rec["expected_matches"] = audit["expected_matches"]
                rec["official_schedule_url"] = audit["source_url"]
                rec["notes"] = (rec.get("notes", "") + " Official round-page census and hashes: data/coverage_italy_women_historical.csv").strip()
        if rec["competition_key"] == "cev_cl" and not rec.get("expected_matches"):
            audit = cev_denominators.get((rec["season"], rec["sex"]))
            if audit:
                rec["expected_matches"] = audit["eligible_completed_fixture_denominator_candidate"]
                rec["official_schedule_url"] = audit["source_urls"].split(" | ")[0]
                rec["notes"] = (rec.get("notes", "") +
                                " Official CEV full LegList plus all discovered phase pages; see local CEV season ledger, including page hashes.").strip()
        if rec["competition_key"] == "plusliga" and not rec.get("expected_matches"):
            audit = plusliga_denominators.get((rec["season"], "regular_season"))
            if audit and audit.get("target_met") == "yes":
                rec["expected_matches"] = audit["expected_matches"]
                rec["official_schedule_url"] = audit.get("roster_source_url") or audit.get("standings_source_url", "")
                rec["notes"] = (rec.get("notes", "") +
                                " Official final standings denominator; see the season-specific PlusLiga coverage report and source inventory for page hashes.").strip()
        key = (str(rec["competition_key"]), str(rec["season"]), str(rec["sex"]))
        season_status = (rec.get("season_status") or "").strip().casefold()
        if not season_status:
            status_match = re.search(r"\bseason_status=(cancelled|in_progress)\b",
                                     rec.get("notes", ""), re.IGNORECASE)
            season_status = status_match.group(1).casefold() if status_match else ""
        # A cancellation or a season still underway is a disposition, not a
        # completed-season archive gap or a zero-match denominator.
        if not season_status and re.search(r"\bcancelled\b", rec.get("notes", ""), re.IGNORECASE):
            season_status = "cancelled"
        if season_status in {"cancelled", "in_progress"}:
            rows.append({**rec, "observed_matches": "",
                         "observed_status": season_status,
                         "coverage_pct": "",
                         "target_pct": float(rec.get("target_pct") or 80),
                         "target_met": "not_applicable",
                         "denominator_status": "not_applicable"})
            continue
        count = observed.get(key, observed.get((key[0], key[1], "*")))
        # The generic VIS table overlaps newer canonical official season
        # tables. Keep the exact-match keyed count for these slices.
        if key in canonical_recent_keys:
            count = recent_results.get(key, count)
            if key[0] == "vnl" and key not in recent_results:
                legacy = silver / ("fivb_legacy_world_grand_prix_2002_03_matches.csv" if key[1].startswith("World Grand Prix") else
                                   "fivb_legacy_world_league_2002_03_matches.csv" if key[1] in {"World League 2002", "World League 2003"} else
                                   "fivb_legacy_world_league_2004_matches.csv")
                if legacy.exists():
                    with legacy.open(encoding="utf-8-sig", newline="") as f:
                        count = sum(1 for r in csv.DictReader(f) if r.get("season") == key[1] and
                                    {"W": "F"}.get(r.get("gender", ""), r.get("gender", "")) == key[2])
        if key[0] == "vnl" and key[1] in {"World League 2006", "World Grand Prix 2006"}:
            # This edition is mirrored by both the compact current table and
            # the VIS batch; select the maximum source's count, not their sum.
            matches_2006 = [
                path for path in (silver / "fivb_lineage_matches.csv", silver / "fivb_vis_matches.csv")
                if path.exists()
            ]
            counts_2006 = []
            for source_path in matches_2006:
                with source_path.open(encoding="utf-8-sig", newline="") as f:
                    c = 0
                    for r in csv.DictReader(f):
                        mapped = _fivb_vnl_key(r)
                        if mapped == key and _valid_completed_outcome(r):
                            c += 1
                    counts_2006.append(c)
            if counts_2006:
                count = max(counts_2006)
        collected = key[0] in available_sources or key in observed
        archive_marker = re.search(r"\bfivb_archive_status=(not_listed|listed_unmanaged)\b",
                                   rec.get("notes", ""), re.IGNORECASE)
        archive_observation = ({"not_listed": "not_listed_in_official_vis_index",
                               "listed_unmanaged": "listed_but_unmanaged_in_vis"}
                              .get(archive_marker.group(1).casefold()) if archive_marker else "")
        rate = (100 * count / float(rec["expected_matches"])) if count is not None and rec.get("expected_matches", "").strip() and float(rec["expected_matches"]) > 0 else ""
        threshold = float(rec.get("target_pct") or 80)
        rows.append({**rec, "observed_matches": count if collected and count is not None else "",
                     "observed_status": ("records_found" if count else archive_observation or "zero_records_in_available_file") if collected else (archive_observation or "source_not_collected"),
                     "coverage_pct": rate,
                     "target_pct": threshold,
                     "target_met": ("yes" if rate != "" and rate >= threshold else "no" if rate != "" else "unknown"),
                     "denominator_status": "verified" if rec.get("expected_matches", "").strip() else "unknown"})
    return rows
