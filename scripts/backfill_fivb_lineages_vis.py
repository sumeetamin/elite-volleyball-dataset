"""Backfill the World League/WGP/VNL lineage from public FIVB VIS records.

The VIS API's returned fixture count supplies the per-edition denominator;
official match numbers are retained and duplicate tournament assignments are
collapsed by match number. VNL 2020 is recorded as cancelled / not applicable.
"""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import re
import time
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.fivb.org/Vis2009/XmlRequest.asmx"
YEARS = range(2000, 2027)
TOURNAMENT_FIELDS = "No Code Name StartDate EndDate"
MATCH_FIELDS = "No NoTournament NoInTournament DateTimeLocal DateTimeUtc MatchPointsA MatchPointsB SetsResultsText Status StatusText MatchResultText ResultTypeText PointsTeamASet1 PointsTeamASet2 PointsTeamASet3 PointsTeamASet4 PointsTeamASet5 PointsTeamBSet1 PointsTeamBSet2 PointsTeamBSet3 PointsTeamBSet4 PointsTeamBSet5"
OUT_FIELDS = ["match_id", "competition_id", "competition_name", "season_id", "edition_year",
              "gender", "team_a_id", "team_a_name", "team_b_id", "team_b_name",
              "scheduled_at_utc", "status", "sets_a", "sets_b", "result_text",
              "sets_results_text", "set_1_a", "set_1_b", "set_2_a", "set_2_b",
              "set_3_a", "set_3_b", "set_4_a", "set_4_b", "set_5_a", "set_5_b",
              "source", "source_record_id", "source_url", "source_sha256", "retrieved_at_utc"]


def request_xml(req: str) -> bytes:
    r = requests.post(API, data={"Request": req}, timeout=90,
                      headers={"User-Agent": "elite-volleyball-dataset/1.0"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    if root.tag == "Error":
        raise RuntimeError(f"FIVB VIS error: {ET.tostring(root, encoding='unicode')}")
    return r.content


def editions_for_year(year: int) -> tuple[int, bytes, list[dict[str, str]]]:
    request = (f'<Request Type="GetVolleyTournamentList" Fields="{TOURNAMENT_FIELDS}">'
               f'<Filter Seasons="{year}" Statuses="Scheduled Running Finished" Genders="M W" />'
               f'</Request>')
    raw = request_xml(request)
    root = ET.fromstring(raw)
    selected = []
    for item in root.findall("VolleyballTournament"):
        name = item.get("Name", "").strip()
        folded = name.casefold()
        if re.search(r"test\s*only|qualif(?:ication|ying|ier)?", folded):
            continue
        if year < 2018:
            if "world league" in folded:
                gender, label = "M", f"World League {year}"
            elif "world grand prix" in folded:
                gender, label = "F", f"World Grand Prix {year}"
            else:
                continue
        else:
            if not re.search(r"volleyball nations league|\bvnl\b", folded):
                continue
            gender = "F" if re.search(r"women|\bW\b", folded) else "M" if re.search(r"men|\bM\b", folded) else ""
            if not gender:
                continue
            label = f"VNL {year}"
        # StartDate is the authoritative edition year when the API season bucket is broad.
        start_year = re.match(r"(\d{4})", item.get("StartDate", ""))
        if start_year and int(start_year.group(1)) != year:
            continue
        selected.append({"no": item.get("No", ""), "code": item.get("Code", ""),
                         "name": name, "gender": gender, "season": label,
                         "year": str(year), "start": item.get("StartDate", ""),
                         "end": item.get("EndDate", "")})
    return int(root.get("NbItems", "0")), raw, selected


def parse_match(item: ET.Element, tournament: dict[str, str], digest: str) -> dict[str, str]:
    def value(name: str) -> str:
        return item.get(name, "").strip()
    a = item.find("TeamA"); b = item.find("TeamB")
    ma = re.fullmatch(r"(\d+)\s*[-:]\s*(\d+)", value("MatchResultText"))
    sets_a, sets_b = (ma.group(1), ma.group(2)) if ma else (value("MatchPointsA"), value("MatchPointsB"))
    result_valid = sets_a.isdigit() and sets_b.isdigit() and max(int(sets_a), int(sets_b)) == 3 and min(int(sets_a), int(sets_b)) <= 2
    points = re.findall(r"(\d+)\s*-\s*(\d+)", value("SetsResultsText"))
    row = {k: "" for k in OUT_FIELDS}
    row.update({"match_id": "FIVB_VIS_" + value("No"),
                "competition_id": "FIVB_TOURNAMENT_" + value("NoTournament"),
                "competition_name": ("FIVB Women's World Grand Prix " if tournament["season"].startswith("World Grand Prix") else
                                     "FIVB Men's World League " if tournament["season"].startswith("World League") else
                                     "FIVB Volleyball Nations League - " + ("Women " if tournament["gender"] == "F" else "Men ")) + tournament["year"],
                "season_id": tournament["year"], "edition_year": tournament["year"],
                "gender": tournament["gender"], "team_a_id": (a.get("Code", "") if a is not None else ""),
                "team_a_name": (a.get("Name", "") if a is not None else ""),
                "team_b_id": (b.get("Code", "") if b is not None else ""),
                "team_b_name": (b.get("Name", "") if b is not None else ""),
                "scheduled_at_utc": value("DateTimeUtc") or value("DateTimeLocal"),
                "status": value("StatusText") or value("Status"),
                "sets_a": sets_a if result_valid else "", "sets_b": sets_b if result_valid else "",
                "result_text": f"{sets_a}-{sets_b}" if result_valid else "",
                "sets_results_text": value("SetsResultsText"),
                "source": "FIVB VIS Web Service", "source_record_id": value("No"),
                "source_url": API, "source_sha256": digest})
    for idx, (pa, pb) in enumerate(points[:5], start=1):
        row[f"set_{idx}_a"], row[f"set_{idx}_b"] = pa, pb
    return row


def main() -> None:
    tournament_cache = ROOT / "data/bronze/fivb_vis_lineage"
    tournament_cache.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str]] = []
    hashes: dict[int, str] = {}
    all_tournaments: list[dict[str, str]] = []
    def fetch_year(y: int):
        return y, editions_for_year(y)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_year, y) for y in YEARS]
        for future in concurrent.futures.as_completed(futures):
            year, (count, raw, editions) = future.result()
            digest = hashlib.sha256(raw).hexdigest()
            hashes[year] = digest
            (tournament_cache / f"tournaments_{year}.xml").write_bytes(raw)
            all_tournaments.extend(editions)
            index_rows.append({"year": str(year), "api_tournament_count": str(count),
                               "matching_editions": str(len(editions)), "source_sha256": digest})
            print(f"VIS tournament index {year}: {len(editions)} matching lineage tournaments", flush=True)
    selected_ids = sorted({t["no"] for t in all_tournaments if t["no"].isdigit()}, key=int)
    if not selected_ids:
        raise RuntimeError("No FIVB World League/WGP/VNL tournament IDs discovered")
    # One official API request for all selected tournament IDs keeps the result
    # census coherent and avoids per-team/page scraping.
    request = (f'<Request Type="GetVolleyMatchList" Fields="{MATCH_FIELDS}">'
               f'<Filter NoTournaments="{" ".join(selected_ids)}" />'
               '<Relation Name="TeamA" Fields="Code Name" />'
               '<Relation Name="TeamB" Fields="Code Name" />'
               '</Request>')
    raw_matches = request_xml(request)
    match_root = ET.fromstring(raw_matches)
    actual = match_root.findall("VolleyballMatch")
    declared = int(match_root.get("NbItems", "-1"))
    if declared != len(actual):
        raise RuntimeError(f"VIS match census mismatch: response says {declared}, parsed {len(actual)}")
    (tournament_cache / "lineage_matches.xml").write_bytes(raw_matches)
    match_digest = hashlib.sha256(raw_matches).hexdigest()
    by_id = {t["no"]: t for t in all_tournaments}
    rows: dict[str, dict[str, str]] = {}
    for match in actual:
        no, tid = match.get("No", ""), match.get("NoTournament", "")
        if not no or tid not in by_id:
            raise RuntimeError(f"Unexpected/missing VIS match identity: {no}/{tid}")
        row = parse_match(match, by_id[tid], match_digest)
        if no in rows and (rows[no]["competition_id"] != row["competition_id"]):
            raise RuntimeError(f"Duplicate official match {no} assigned to multiple tournament IDs")
        rows[no] = row
    sorted_rows = sorted(rows.values(), key=lambda r: (r["edition_year"], r["gender"], r["scheduled_at_utc"], r["match_id"]))
    silver = ROOT / "data/silver/fivb_lineage_matches.csv"
    with silver.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS); w.writeheader(); w.writerows(sorted_rows)
    # Per edition: official API fixture IDs are the denominator; results with
    # valid final set scores are the numerator. A cancelled edition has no gate.
    coverage: list[dict[str, str]] = []
    editions: dict[tuple[str, str], list[dict[str, str]]] = {}
    for t in all_tournaments:
        editions.setdefault((t["gender"], t["season"]), []).append(t)
    for (gender, season), ts in sorted(editions.items()):
        selected = [r for r in sorted_rows if r["gender"] == gender and
                    ((season.startswith("World League") and r["edition_year"] == season.split()[-1] and "World League" in r["competition_name"]) or
                     (season.startswith("World Grand Prix") and r["edition_year"] == season.split()[-1] and "World Grand Prix" in r["competition_name"]) or
                     (season.startswith("VNL") and r["edition_year"] == season.split()[-1] and "Nations League" in r["competition_name"]))]
        # The API may group several pools/finals. The unique match IDs form the edition census.
        expected = sum(1 for m in actual if m.get("NoTournament") in {t["no"] for t in ts})
        complete = sum(bool(r["sets_a"] and r["sets_b"]) for r in selected)
        coverage.append({"competition_key": "vnl", "competition": "FIVB international lineage", "sex": gender,
                         "season": season, "phase": "all_official_tournament_matches", "expected_matches": str(expected),
                         "observed_matches": str(complete), "dated_matches": str(sum(bool(r["scheduled_at_utc"]) for r in selected)),
                         "coverage_pct": f"{100*complete/expected:.2f}" if expected else "",
                         "date_coverage_pct": f"{100*sum(bool(r['scheduled_at_utc']) for r in selected)/expected:.2f}" if expected else "",
                         "denominator_method": "FIVB VIS GetVolleyTournamentList + GetVolleyMatchList official unique match numbers; all associated groups/finals deduplicated",
                         "source_url": API, "tournament_ids": " ".join(t["no"] for t in ts),
                         "source_sha256": match_digest, "target_met": "yes" if expected and complete/expected >= .8 else "no" if expected else "unknown"})
    # Explicit cancellations are dispositions, not zero-coverage failures.
    for gender in ("M", "F"):
        coverage.append({"competition_key":"vnl", "competition":"FIVB international lineage", "sex":gender,
                         "season":"VNL 2020", "phase":"cancelled", "expected_matches":"", "observed_matches":"",
                         "dated_matches":"", "coverage_pct":"", "date_coverage_pct":"",
                         "denominator_method":"VNL 2020 cancelled; no edition played", "source_url":API,
                         "tournament_ids":"", "source_sha256":"", "target_met":"not_applicable"})
    with (ROOT / "reports/fivb_lineage_vis_coverage.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(coverage[0])); w.writeheader(); w.writerows(coverage)
    with (ROOT / "reports/fivb_lineage_vis_tournament_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(index_rows[0])); w.writeheader(); w.writerows(sorted(index_rows,key=lambda r:int(r['year'])))
    # Keep the project-wide scope/coverage ledger in sync with the source export.
    config_path = ROOT / "config/competition_seasons.csv"
    configs = list(csv.DictReader(config_path.open(encoding="utf-8-sig", newline="")))
    by_slice = {(r["sex"], r["season"]): r for r in coverage}
    for r in configs:
        entry = by_slice.get((r["sex"], r["season"])) if r["competition_key"] == "vnl" else None
        if not entry:
            continue
        if entry["expected_matches"] == "0":
            r["expected_matches"] = ""
            r["official_schedule_url"] = API
            r["notes"] = "VIS lists this edition, but its public match-list API returns no match rows; denominator remains unverified."
            continue
        r["expected_matches"] = entry["expected_matches"]
        r["official_schedule_url"] = API
        r["notes"] = "Official FIVB VIS tournament and match IDs; groups/finals combined and duplicate match IDs removed. See reports/fivb_lineage_vis_coverage.csv."
        if entry["target_met"] == "not_applicable":
            r["expected_matches"] = ""
            r["notes"] = "VNL 2020 was cancelled; no edition played."
    with config_path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(configs[0])); w.writeheader(); w.writerows(configs)
    ledger_path = ROOT / "reports/coverage_audit_current.csv"
    ledger = list(csv.DictReader(ledger_path.open(encoding="utf-8-sig", newline="")))
    for r in ledger:
        entry = by_slice.get((r["sex"], r["season"])) if r["competition_key"] == "vnl" else None
        if not entry:
            continue
        if entry["expected_matches"] == "0":
            r.update(expected_matches="", observed_matches="", observed_status="no_match_list_returned",
                     coverage_pct="", target_met="unknown", denominator_status="unknown")
        elif entry["target_met"] == "not_applicable":
            r.update(expected_matches="", observed_matches="", observed_status="cancelled",
                     coverage_pct="", target_met="not_applicable", denominator_status="not_applicable")
        else:
            r.update(expected_matches=entry["expected_matches"], observed_matches=entry["observed_matches"],
                     observed_status="verified_official_vis", coverage_pct=entry["coverage_pct"],
                     target_met=entry["target_met"], denominator_status="verified")
    with ledger_path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(ledger[0])); w.writeheader(); w.writerows(ledger)
    print(f"Unique official matches: {len(sorted_rows)}; result rows: {sum(bool(r['sets_a']) for r in sorted_rows)}; edition slices: {len(coverage)}", flush=True)


if __name__ == "__main__":
    main()
