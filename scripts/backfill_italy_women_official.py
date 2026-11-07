"""Collect official Serie A1 women regular-season fixture pages by season/round.

Raw pages and normalized rows remain local. A season denominator is accepted
only when every distinct official round page is retrieved and parsed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.legavolleyfemminile.it/risultati/"
RAW = ROOT / "data" / "bronze" / "italy_women"
SILVER = ROOT / "data" / "silver" / "italy_serie_a1_women_matches.csv"
COVERAGE = ROOT / "data" / "coverage_italy_women_historical.csv"
FIELDS = ("competition_key", "sex", "season", "phase", "round", "source_match_id", "match_date",
          "home_team", "away_team", "home_sets", "away_sets", "status", "source_url", "source_sha256",
          "disposition_source_url")
COVID_2019_20_NOTICE = "https://www.legavolleyfemminile.it/igor-il-campionato-di-serie-a1-e-sospeso-definitivamente/"


def _fetch(url: str, cache: Path, refresh: bool = False) -> tuple[bytes, str]:
    if not refresh and cache.exists():
        return cache.read_bytes(), hashlib.sha256(cache.read_bytes()).hexdigest()
    request = Request(url, headers={"User-Agent": "EliteVolleyballDataset/0.1 (historical research)"})
    with urlopen(request, timeout=30) as response:
        payload = response.read()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(payload)
    time.sleep(0.3)
    return payload, hashlib.sha256(payload).hexdigest()


def _query_links(soup: BeautifulSoup, key: str) -> list[tuple[str, str]]:
    links = []
    for anchor in soup.select("a[href]"):
        url = anchor.get("href", "")
        if urlparse(url).netloc != "www.legavolleyfemminile.it":
            continue
        if key not in parse_qs(urlparse(url).query):
            continue
        links.append((anchor.get_text(" ", strip=True), url))
    return links


def _season_label(soup: BeautifulSoup) -> str:
    anchor = soup.select_one("#filtroStagione")
    if not anchor:
        raise ValueError("No selected season label")
    match = re.search(r"(20\d{2})\s*/\s*(?:20)?(\d{2})", anchor.get_text(" ", strip=True))
    if not match:
        raise ValueError("Unrecognized selected season label")
    return f"{match.group(1)}/{match.group(2)}"


def _regular_competition(soup: BeautifulSoup) -> str:
    candidates = []
    for label, url in _query_links(soup, "campionato"):
        folded = label.casefold()
        if ("a1" in folded and ("regular" in folded or folded.startswith("serie a1") or folded.startswith("lvf a1"))
                and not any(word in folded for word in ("play", "coppa", "supercoppa", "challenge"))):
            candidates.append(url)
    ids = {parse_qs(urlparse(url).query)["campionato"][0] for url in candidates}
    if len(ids) != 1:
        raise ValueError(f"Expected one Serie A1 regular-season competition; found {sorted(ids)}")
    return next(iter(ids))


def _round_links(soup: BeautifulSoup, competition_id: str, year: int) -> list[tuple[str, str]]:
    rounds = {}
    for label, url in _query_links(soup, "giornata"):
        params = parse_qs(urlparse(url).query)
        if (params.get("campionato") == [competition_id] and params.get("stagione") == [str(year)]
                and params["giornata"][0] != "0" and label.strip().casefold() != "tutte"):
            rounds[params["giornata"][0]] = (label, url)
    if not rounds:
        raise ValueError("Official page has no round links")
    return list(rounds.values())


def _parse_round(payload: bytes, season: str, round_name: str, url: str, sha: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(payload, "html.parser")
    rows = []
    for table in soup.select("table.risultati"):
        heads = table.select("thead th")
        teams = table.select("tbody tr")
        if len(heads) < 2 or len(teams) != 2:
            raise ValueError(f"Malformed match table at {url}")
        date_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", table.select_one("thead").get_text(" ", strip=True))
        played = datetime.strptime(date_match.group(1), "%d/%m/%Y").date() if date_match else None
        start_year = int(season[:4])
        if played and not (date(start_year, 7, 1) <= played <= date(start_year + 1, 6, 30)):
            raise ValueError(f"Fixture outside named club season: {url} {played} {season}")
        parsed_teams = []
        for tr in teams:
            score_text = tr.select_one(".num")
            name_link = tr.select_one("td a")
            if score_text is None or name_link is None:
                raise ValueError(f"Missing team or score at {url}")
            parsed_teams.append((name_link.get_text(" ", strip=True), score_text.get_text(strip=True)))
        match_center = table.select_one('a[href*="/match-center/"]')
        official_id = re.search(r"/match-center/(\d+)", match_center["href"]).group(1) if match_center else ""
        if not official_id or official_id == "0":
            identity = "|".join((season, round_name, played.isoformat() if played else "", *(team for team, _ in parsed_teams)))
            official_id = "fallback_" + hashlib.sha256(identity.encode()).hexdigest()[:20]
        try:
            home_sets, away_sets = (int(score) for _, score in parsed_teams)
        except ValueError:
            home_sets = away_sets = -1
        valid = max(home_sets, away_sets) == 3 and min(home_sets, away_sets) in (0, 1, 2)
        rows.append({"competition_key": "italy_serie_a1_women", "sex": "F", "season": season,
                     "phase": "regular_season", "round": round_name, "source_match_id": official_id,
                     "match_date": played.isoformat() if played else "", "home_team": parsed_teams[0][0], "away_team": parsed_teams[1][0],
                     "home_sets": home_sets if valid else "", "away_sets": away_sets if valid else "",
                     "status": "completed" if valid else "unknown", "source_url": url, "source_sha256": sha,
                     "disposition_source_url": ""})
    if not rows:
        raise ValueError(f"No match tables on official round page: {url}")
    return rows


def collect_season(year: int, refresh: bool = False) -> tuple[list[dict[str, str]], dict[str, str]]:
    initial_url = f"{BASE}?serie=1&stagione={year}"
    initial, _ = _fetch(initial_url, RAW / f"{year}_index.html", refresh)
    initial_soup = BeautifulSoup(initial, "html.parser")
    season = _season_label(initial_soup)
    if season != f"{year}/{(year + 1) % 100:02d}":
        raise ValueError(f"Query year {year} returned season {season}")
    competition_id = _regular_competition(initial_soup)
    competition_url = f"{BASE}?serie=1&campionato={competition_id}&stagione={year}"
    competition, _ = _fetch(competition_url, RAW / f"{year}_regular_index.html", refresh)
    rounds = _round_links(BeautifulSoup(competition, "html.parser"), competition_id, year)
    matches = {}
    hashes = []
    for round_name, url in rounds:
        round_id = parse_qs(urlparse(url).query)["giornata"][0]
        payload, sha = _fetch(url, RAW / f"{year}_{round_id}.html", refresh)
        hashes.append(sha)
        for row in _parse_round(payload, season, round_name, url, sha):
            key = row["source_match_id"]
            if key in matches and (row["home_team"], row["away_team"]) != (matches[key]["home_team"], matches[key]["away_team"]):
                raise ValueError(f"Conflicting official match ID {key} in {season}")
            matches[key] = row
    if season == "2019/20":
        for row in matches.values():
            if row["status"] == "unknown":
                row["status"] = "cancelled"
                row["disposition_source_url"] = COVID_2019_20_NOTICE
    completed = sum(row["status"] == "completed" for row in matches.values())
    dated_results = sum(row["status"] == "completed" and bool(row["match_date"]) for row in matches.values())
    cancelled = sum(row["status"] == "cancelled" for row in matches.values())
    return list(matches.values()), {"competition_key": "italy_serie_a1_women", "sex": "F", "season": season,
                                     "competition_id": competition_id, "rounds_fetched": str(len(rounds)),
                                     "scheduled_fixtures": str(len(matches)), "cancelled_fixtures": str(cancelled),
                                     "expected_matches": str(len(matches) - cancelled), "completed_results": str(completed),
                                     "dated_results": str(dated_results),
                                     "source_url": competition_url, "page_hashes_sha256": ";".join(hashes),
                                     "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.end_year < args.start_year:
        parser.error("end-year must be at least start-year")
    all_rows = []
    coverage = []
    for year in range(args.start_year, args.end_year + 1):
        try:
            rows, summary = collect_season(year, args.refresh)
        except Exception as exc:
            print(f"{year}: {exc}", file=sys.stderr)
            continue
        all_rows.extend(rows)
        coverage.append(summary)
        print(f"{summary['season']}: {summary['completed_results']}/{summary['expected_matches']} over {summary['rounds_fetched']} rounds")
    if not coverage:
        raise SystemExit("No seasons collected")
    # Merge with earlier season captures so a targeted rerun preserves them.
    existing = {}
    if SILVER.exists():
        with SILVER.open(encoding="utf-8-sig", newline="") as f:
            existing = {(r["season"], r["source_match_id"]): r for r in csv.DictReader(f)}
    existing.update({(r["season"], r["source_match_id"]): r for r in all_rows})
    _write_csv(SILVER, FIELDS, list(existing.values()))
    summaries = {}
    if COVERAGE.exists():
        with COVERAGE.open(encoding="utf-8-sig", newline="") as f:
            summaries = {r["season"]: r for r in csv.DictReader(f)}
    summaries.update({r["season"]: r for r in coverage})
    _write_csv(COVERAGE, tuple(coverage[0].keys()), list(summaries.values()))


if __name__ == "__main__":
    main()
