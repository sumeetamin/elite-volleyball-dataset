"""Backfill Lega Volley men's first-division match results from official calendars.

The source calendar is queried by season start year. The script discovers the
official regular-season competition ID from the page itself, downloads both
legs, imports completed scores using the existing ID-based parser, and counts
distinct official fixture IDs for the season denominator. Raw HTML is retained
locally and should only be redistributed if the source terms permit it.
"""
from __future__ import annotations

import csv
import hashlib
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from volleyball_dataset.import_italy import import_superlega_page  # noqa: E402

BASE = "https://ww2.legavolley.it/Calendario.asp"
RAW_DIR = ROOT / "data" / "bronze"
SILVER = ROOT / "data" / "silver" / "italy_superlega_matches_2000_2026.csv"
COVERAGE = ROOT / "data" / "coverage_italy_superlega_historical.csv"


class _SeasonPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._in_competitions = False
        self.competition_options: list[tuple[str, str]] = []
        self._option_value = ""
        self._option_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "select" and attributes.get("id") == "Campionato":
            self._in_competitions = True
        if tag == "option" and self._in_competitions:
            self._option_value = attributes.get("value") or ""
            self._option_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "option" and self._option_value:
            self.competition_options.append((self._option_value, " ".join(self._option_text).strip()))
            self._option_value = ""
            self._option_text = []
        if tag == "select" and self._in_competitions:
            self._in_competitions = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_competitions and self._option_value:
            self._option_text.append(data)


def get_page(year: int, **params: object) -> tuple[str, bytes]:
    query = urlencode({"Anno": year, **params})
    url = f"{BASE}?{query}"
    request = Request(url, headers={"User-Agent": "EliteVolleyballDataset/0.1 (historical research)"})
    with urlopen(request, timeout=30) as response:
        payload = response.read()
    # Keep requests paced; this is a public historical archive, not a bulk API.
    time.sleep(0.2)
    return url, payload


def discover_regular_season_id(html: bytes) -> tuple[str, str]:
    parser = _SeasonPageParser()
    parser.feed(html.decode("latin-1", errors="replace"))
    title = re.sub(r"\s+", " ", parser.title).strip()
    match = re.search(r"Calendario\s+(\d{4})/(\d{4})", title, re.I)
    if not match:
        raise ValueError(f"Could not read season from official calendar title: {title!r}")
    season = f"{match.group(1)}/{match.group(2)[-2:]}"
    if not parser.competition_options:
        raise ValueError(f"No competition selector on calendar page for {season}")
    candidates = []
    for value, option_label in parser.competition_options:
        label = unescape(option_label)
        value = value.strip()
        normalized = label.casefold()
        if value.isdigit() and "regular season" in normalized and ("superlega" in normalized or "a1" in normalized):
            candidates.append((value, label))
    if len(candidates) != 1:
        raise ValueError(f"Expected one official A1 regular-season option for {season}; found {candidates}")
    return season, candidates[0][0]


def official_fixture_ids(payload: bytes) -> set[str]:
    text = payload.decode("latin-1", errors="replace")
    fixtures: set[str] = set()
    # Match links are embedded in each fixture row, including unplayed games.
    for row in re.findall(r"<tr\b.*?</tr>", text, flags=re.I | re.S):
        if re.search(r"class\s*=\s*['\"]Dettaglio(?:Ris)?Cal", row, flags=re.I):
            fixtures.update(re.findall(r"IdGara\s*=\s*(\d+)", row, flags=re.I))
    return fixtures


def official_team_ids(payload: bytes) -> set[str]:
    text = payload.decode("latin-1", errors="replace")
    teams: set[str] = set()
    for tag in re.findall(r"<td\b[^>]*>", text, flags=re.I):
        if re.search(r"class\s*=\s*['\"]DettaglioCal", tag, flags=re.I):
            match = re.search(r"IdSquadra\s*=\s*(\d+)", tag, flags=re.I)
            if match:
                teams.add(match.group(1))
    return teams


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def backfill(start_year: int = 2000, end_year: int = 2026) -> tuple[int, int]:
    all_matches: dict[tuple[str, str], dict[str, str]] = {}
    season_audits: list[dict[str, object]] = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cached_audit = {}
    if COVERAGE.exists():
        cached_audit = {row["season"]: row for row in _read_csv(COVERAGE)}

    for year in range(start_year, end_year + 1):
        season = f"{year}/{(year + 1) % 100:02d}"
        old_audit = cached_audit.get(season, {})
        discovery_url = f"{BASE}?{urlencode({'Anno': year})}"
        discovery_payload = b""
        competition_id = str(old_audit.get("competition_id", ""))
        if not competition_id:
            discovery_url, discovery_payload = get_page(year)
            season, competition_id = discover_regular_season_id(discovery_payload)
        fixture_ids: set[str] = set()
        team_ids: set[str] = set()
        season_rows: dict[str, dict[str, str]] = {}
        raw_hashes: list[str] = []
        source_urls: list[str] = []
        retrieved_times: list[str] = []
        if old_audit.get("source_sha256"):
            old_hashes = str(old_audit["source_sha256"]).split(";")
            if len(old_hashes) == 3:
                discovery_payload_hash = old_hashes[0]
            else:
                discovery_payload_hash = ""
        else:
            discovery_payload_hash = hashlib.sha256(discovery_payload).hexdigest() if discovery_payload else ""

        for phase, leg in ((1, "first"), (2, "return")):
            url = (f"{BASE}?{urlencode({'Anno': year, 'IdCampionato': competition_id, 'IdFase': phase, 'IdSquadra': 0})}")
            raw_path = RAW_DIR / f"italy_superlega_{season.replace('/', '_')}_{leg}_leg.html"
            if raw_path.exists():
                payload = raw_path.read_bytes()
            else:
                url, payload = get_page(year, IdCampionato=competition_id, IdFase=phase, IdSquadra=0)
                raw_path.write_bytes(payload)
            source_urls.append(url)
            raw_hashes.append(hashlib.sha256(payload).hexdigest())
            fixture_ids.update(official_fixture_ids(payload))
            team_ids.update(official_team_ids(payload))
            retrieved_times.append(datetime.fromtimestamp(raw_path.stat().st_mtime, timezone.utc).isoformat())

            temp_output = ROOT / "data" / "quarantine" / f"italy_{year}_{leg}.csv"
            temp_coverage = ROOT / "data" / "quarantine" / f"italy_{year}_{leg}_coverage.csv"
            import_superlega_page(raw_path, temp_output, temp_coverage, season, url)
            for row in _read_csv(temp_output):
                key = row["source_match_id"]
                previous = season_rows.get(key)
                if previous and (previous["home_team"], previous["away_team"], previous["home_sets"], previous["away_sets"]) != (row["home_team"], row["away_team"], row["home_sets"], row["away_sets"]):
                    raise ValueError(f"Conflicting official result for {season} match ID {key}")
                season_rows[key] = row
            temp_output.unlink(missing_ok=True)
            temp_coverage.unlink(missing_ok=True)

        if not fixture_ids or not team_ids:
            raise ValueError(f"Official calendar returned no fixture/team IDs for {season}: {discovery_url}")
        if not set(season_rows).issubset(fixture_ids):
            raise ValueError(f"Imported result IDs are not contained in fixture census for {season}")
        expected_matches = len(team_ids) * (len(team_ids) - 1)
        result_coverage = len(season_rows) / expected_matches
        season_status = "in_progress" if year == datetime.now(timezone.utc).year else ("ended_early" if len(fixture_ids) < expected_matches else "completed")
        for match_id, row in season_rows.items():
            all_matches[(season, match_id)] = row

        season_audits.append({
            "competition_key": "italy_superlega", "competition": "Italian SuperLega",
            "sex": "M", "season": season, "competition_id": competition_id,
            "participating_teams": len(team_ids), "expected_matches_double_round_robin": expected_matches,
            "official_match_ids_observed": len(fixture_ids), "completed_results": len(season_rows),
            "result_coverage_pct": round(100 * result_coverage, 4),
            "target_pct": 80,
            "target_met": "not_yet_assessed" if season_status == "in_progress" else ("yes" if result_coverage >= .8 else "no"),
            "season_status": season_status,
            "scheduled_or_unresolved_matches": expected_matches - len(season_rows),
            "source_urls": ";".join([discovery_url, *source_urls]),
            "source_sha256": ";".join([discovery_payload_hash, *raw_hashes]),
            "retrieved_at_utc": ";".join(retrieved_times),
            "denominator_method": "official participant IDs in both regular-season leg pages x (teams - 1), double round-robin home/away format; cross-check available IdGara values",
        })
        print(f"{season}: {len(season_rows)}/{expected_matches} completed results ({season_status}; {competition_id})")

    # A range refresh must retain seasons outside the requested range, including
    # the browser-captured 1999/2000 boundary season.
    audited = {row["season"] for row in season_audits}
    if SILVER.exists():
        for row in _read_csv(SILVER):
            if row["season"] not in audited:
                all_matches.setdefault((row["season"], row["source_match_id"]), row)
    if all_matches:
        first_row = next(iter(all_matches.values()))
        _write_csv(SILVER, list(all_matches.values()), list(first_row))
    season_audits.extend(row for season, row in cached_audit.items() if season not in audited)
    _write_csv(COVERAGE, season_audits, list(season_audits[0]) if season_audits else [])
    return len(all_matches), len(season_audits)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2000)
    parser.add_argument("--end-year", type=int, default=2026)
    args = parser.parse_args()
    matches, seasons = backfill(args.start_year, args.end_year)
    print(f"Imported {matches} completed results across {seasons} seasons")
