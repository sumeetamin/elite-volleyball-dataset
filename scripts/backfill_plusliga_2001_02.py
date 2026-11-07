"""Backfill one official PlusLiga season's results and dates.

The official site exposes results through all-time team-pair pages and exact
dates through the team-by-season pages. Raw pages, match rows and CSV reports
are local/ignored until redistribution rights are reviewed.
"""
from __future__ import annotations

import csv
import hashlib
import itertools
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from volleyball_dataset.import_polish_head_to_head import (  # noqa: E402
    FIELDS as MATCH_FIELDS,
    parse_head_to_head_page,
    parse_official_season_roster,
)

SEASON = "2001/02"
TOUR_ID = 2
EXPECTED_TEAMS = 10
EXPECTED_GAMES_PER_TEAM = 18
BASE = "https://www.plusliga.pl"
PAIR_URL = (BASE + "/statsTeams/teams_1/{team_a}/teams_2/{team_b}/"
            "type/teamsComparator/nocookies/1.html")
TEAM_URL = BASE + "/teams/id/{team_id}/tour/{tour}/nocookies/1.html"


def _fetch(url: str, path: Path, refresh: bool = False) -> tuple[bytes, str]:
    if path.exists() and not refresh:
        payload = path.read_bytes()
    else:
        request = Request(url, headers={
            "User-Agent": "EliteVolleyballDataset/0.1 (historical research)",
        })
        with urlopen(request, timeout=45) as response:
            payload = response.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        time.sleep(0.2)
    return payload, hashlib.sha256(payload).hexdigest()


def parse_team_season_dates(payload: bytes, season: str = SEASON) -> dict[str, str]:
    """Extract official game IDs and dates from a team-season profile page."""
    soup = BeautifulSoup(payload, "html.parser")
    dates: dict[str, str] = {}
    for node in soup.select('div[id^="charttooltip"]'):
        match = re.fullmatch(r"charttooltip(\d+)", node.get("id", ""))
        if not match:
            continue
        date_node = node.select_one("p.date")
        if date_node is None:
            continue
        date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", date_node.get_text(" ", strip=True))
        if not date_match:
            continue
        parsed = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
        start_year = int(season[:4])
        if parsed < datetime(start_year, 7, 1).date() or parsed > datetime(start_year + 1, 6, 30).date():
            continue
        source_id = match.group(1)
        day = parsed.isoformat()
        old = dates.get(source_id)
        if old and old != day:
            raise ValueError(f"Official team pages disagree on date for game {source_id}: {old} vs {day}")
        dates[source_id] = day
    return dates


def merge_team_dates(matches: dict[str, dict[str, object]],
                     team_dates: dict[str, str], require_all: bool = True) -> int:
    """Attach dates by stable official game ID and reject result conflicts."""
    unmatched = set(team_dates) - set(matches)
    if unmatched:
        raise ValueError(f"Team-season page IDs absent from pair archive: {sorted(unmatched)[:8]}")
    missing = []
    dated_regular = 0
    for source_id, row in matches.items():
        match_date = team_dates.get(source_id)
        if not match_date:
            if row.get("phase") == "regular_season":
                missing.append(source_id)
            continue
        row["match_date"] = match_date
        if row.get("phase") == "regular_season":
            dated_regular += 1
    if missing and require_all:
        raise ValueError(f"Regular-season results lack team-page dates: {len(missing)}; sample {missing[:8]}")
    return dated_regular


def parse_match_detail_date(payload: bytes, expected: dict[str, object]) -> str:
    """Read and cross-check the date, teams, and set result on an official game page."""
    soup = BeautifulSoup(payload, "html.parser")
    date_node = soup.select_one(".game-date")
    if date_node is None:
        raise ValueError(f"Official game page {expected['source_match_id']} has no game date")
    date_match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", date_node.get_text(" ", strip=True))
    if not date_match:
        raise ValueError(f"Official game page {expected['source_match_id']} has an unrecognized date")
    headings = [node.get_text(" ", strip=True) for node in soup.select("h2")]
    matchup = next((text for text in headings if re.search(r"\s+vs\s+", text, re.I)), None)
    if matchup is None:
        raise ValueError(f"Official game page {expected['source_match_id']} has no matchup heading")
    home, away = re.split(r"\s+vs\s+", matchup, maxsplit=1, flags=re.I)
    away = re.sub(r"\s+Trwa!?$", "", away).strip()

    def canonical(name: object) -> str:
        folded = unicodedata.normalize("NFKD", str(name)).casefold()
        return "".join(ch for ch in folded if ch.isalnum())

    if canonical(home) != canonical(expected["home_team"]) or canonical(away) != canonical(expected["away_team"]):
        raise ValueError(f"Official game page {expected['source_match_id']} matchup does not match pair archive")
    score_node = soup.select_one(".score")
    score = re.findall(r"\d+", score_node.get_text(" ", strip=True)) if score_node else []
    if len(score) < 2 or (int(score[0]), int(score[1])) != (int(expected["home_sets"]), int(expected["away_sets"])):
        raise ValueError(f"Official game page {expected['source_match_id']} score does not match pair archive")
    return datetime.strptime(date_match.group(1), "%d.%m.%Y").date().isoformat()


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _season_paths(season: str) -> tuple[str, Path, Path, Path, Path]:
    start, end = season.split("/")
    slug = f"{start}_{end}"
    return (
        slug,
        ROOT / "data" / "bronze" / f"plusliga_m_{slug}",
        ROOT / "data" / "silver" / f"plusliga_m_{slug}_matches.csv",
        ROOT / "reports" / f"plusliga_m_{slug}_coverage.csv",
        ROOT / "reports" / f"plusliga_m_{slug}_source_inventory.csv",
    )


def backfill_season(season: str = SEASON, tour_id: int = TOUR_ID,
                    expected_teams: int = EXPECTED_TEAMS,
                    expected_games_per_team: int = EXPECTED_GAMES_PER_TEAM,
                    refresh: bool = False, detail_fallback: bool = False) -> tuple[int, int]:
    slug, raw_dir, output, coverage_report, source_report = _season_paths(season)
    provenance_report = ROOT / "reports" / f"plusliga_m_{slug}_provenance.md"
    roster_url = f"{BASE}/table/tour/{tour_id}/nocookies/1.html"
    raw_dir.mkdir(parents=True, exist_ok=True)
    roster_payload, roster_hash = _fetch(roster_url, raw_dir / "final_standings.html", refresh)
    roster = parse_official_season_roster(roster_payload)
    team_ids = sorted(roster, key=int)
    games_per_team = {int(info["matches_played"]) for info in roster.values()}
    if len(roster) != expected_teams or games_per_team != {expected_games_per_team}:
        raise ValueError(f"Expected {expected_teams} teams with {expected_games_per_team} regular matches each; got {len(roster)} teams and {sorted(games_per_team)}")

    matches: dict[str, dict[str, object]] = {}
    source_rows: list[dict[str, object]] = [{
        "page_type": "official_final_standings", "team_a_id": "", "team_b_id": "",
        "source_url": roster_url, "source_sha256": roster_hash,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "parsed_rows": len(roster),
    }]
    pairs = list(itertools.combinations(team_ids, 2))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for team_a, team_b in pairs:
            url = PAIR_URL.format(team_a=team_a, team_b=team_b)
            path = raw_dir / f"pair_{team_a}_{team_b}.html"
            futures[pool.submit(_fetch, url, path, refresh)] = (team_a, team_b, url)
        for future in as_completed(futures):
            team_a, team_b, url = futures[future]
            payload, digest = future.result()
            rows = parse_head_to_head_page(payload, url, "plusliga", season, "M")
            for row in rows:
                source_id = str(row["source_match_id"])
                old = matches.get(source_id)
                identity = ("home_team", "away_team", "home_sets", "away_sets", "phase")
                if old and any(old[k] != row[k] for k in identity):
                    raise ValueError(f"Conflicting result for official PlusLiga ID {source_id}")
                matches[source_id] = row
            source_rows.append({
                "page_type": "team_pair_archive", "team_a_id": team_a, "team_b_id": team_b,
                "source_url": url, "source_sha256": digest,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(), "parsed_rows": len(rows),
            })

    # Every unique fixture appears on both participating team profiles. Merge
    # the dates by official games/id rather than by the potentially changing names.
    team_dates: dict[str, str] = {}
    team_date_sources: dict[str, tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for team_id in team_ids:
            url = TEAM_URL.format(team_id=team_id, tour=tour_id)
            path = raw_dir / f"team_{team_id}_tour_{tour_id}.html"
            futures[pool.submit(_fetch, url, path, refresh)] = (team_id, url)
        for future in as_completed(futures):
            team_id, url = futures[future]
            payload, digest = future.result()
            dates = parse_team_season_dates(payload, season)
            for match_id, match_date in dates.items():
                previous = team_dates.get(match_id)
                if previous and previous != match_date:
                    raise ValueError(f"Team-season pages disagree on date for game {match_id}")
                team_dates[match_id] = match_date
                old_source = team_date_sources.get(match_id)
                candidate = (url, digest)
                if old_source is None or candidate[0] < old_source[0]:
                    team_date_sources[match_id] = candidate
            source_rows.append({
                "page_type": "team_season_results", "team_a_id": team_id, "team_b_id": "",
                "source_url": url, "source_sha256": digest,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(), "parsed_rows": len(dates),
            })

    try:
        dated_regular = merge_team_dates(matches, team_dates)
    except ValueError as exc:
        if not detail_fallback or "Team-season page IDs absent from pair archive" not in str(exc):
            raise
        dated_regular = 0
        detail_rows = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {}
            for source_id, row in matches.items():
                url = f"{BASE}/games/id/{source_id}/nocookies/1.html"
                path = raw_dir / f"game_{source_id}.html"
                futures[pool.submit(_fetch, url, path, refresh)] = (source_id, row, url)
            for future in as_completed(futures):
                source_id, row, url = futures[future]
                payload, digest = future.result()
                row["match_date"] = parse_match_detail_date(payload, row)
                row["date_source_url"], row["date_source_sha256"] = url, digest
                if row["phase"] == "regular_season":
                    dated_regular += 1
                detail_rows.append({
                    "page_type": "official_match_detail", "team_a_id": "", "team_b_id": "",
                    "source_url": url, "source_sha256": digest,
                    "captured_at_utc": datetime.now(timezone.utc).isoformat(), "parsed_rows": 1,
                })
        source_rows.extend(detail_rows)
    regular = [row for row in matches.values() if row["phase"] == "regular_season"]
    playoffs = [row for row in matches.values() if row["phase"] == "playoffs"]
    playouts = [row for row in matches.values() if row["phase"] == "playouts"]
    expected = len(roster) * expected_games_per_team // 2
    if len(regular) != expected or dated_regular != len(regular):
        raise ValueError(f"Coverage validation failed: regular {len(regular)}/{expected}; dated {dated_regular}/{len(regular)}")

    out_fields = MATCH_FIELDS + ["date_source_url", "date_source_sha256"]
    for row in matches.values():
        # Keep season-specific exact-date lineage separate from the result source.
        if not row.get("date_source_url"):
            row["date_source_url"], row["date_source_sha256"] = team_date_sources.get(str(row["source_match_id"]), ("", ""))
    ordered = sorted(matches.values(), key=lambda row: (str(row["phase"]), str(row["match_date"]), int(str(row["source_match_id"]))))
    _write_csv(output, out_fields, ordered)
    _write_csv(source_report, list(source_rows[0]), source_rows)
    report = [{
        "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
        "season": season, "phase": "regular_season", "participating_teams": len(roster),
        "games_per_team": expected_games_per_team, "expected_matches": expected,
        "observed_matches": len(regular), "dated_matches": dated_regular,
        "coverage_pct": round(100 * len(regular) / expected, 4), "date_coverage_pct": 100.0,
        "target_pct": 80, "target_met": "yes", "pair_pages_parsed": len(pairs),
        "team_pages_parsed": len(team_ids), "standings_source_url": roster_url,
        "standings_source_sha256": roster_hash,
        "denominator_method": f"official final table: {len(roster)} teams x {expected_games_per_team} GP / 2; unique official game IDs from all {len(pairs)} pair pages",
    }, {
        "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
        "season": season, "phase": "playoffs", "participating_teams": len(roster),
        "games_per_team": "", "expected_matches": "", "observed_matches": len(playoffs),
        "dated_matches": sum(bool(row.get("match_date")) for row in playoffs),
        "coverage_pct": "", "date_coverage_pct": "", "target_pct": 80,
        "target_met": "unknown", "pair_pages_parsed": len(pairs), "team_pages_parsed": len(team_ids),
        "standings_source_url": roster_url, "standings_source_sha256": roster_hash,
        "denominator_method": "Playoff outcomes kept separate; no verified playoff denominator.",
    }, {
        "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
        "season": season, "phase": "playouts", "participating_teams": len(roster),
        "games_per_team": "", "expected_matches": "", "observed_matches": len(playouts),
        "dated_matches": sum(bool(row.get("match_date")) for row in playouts),
        "coverage_pct": "", "date_coverage_pct": "", "target_pct": 80,
        "target_met": "unknown", "pair_pages_parsed": len(pairs), "team_pages_parsed": len(team_ids),
        "standings_source_url": roster_url, "standings_source_sha256": roster_hash,
        "denominator_method": "Play-out outcomes kept separate; no verified play-out denominator.",
    }]
    _write_csv(coverage_report, list(report[0]), report)
    csv_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    lines = [
        f"# PlusLiga men {season} backfill", "",
        f"Standings source: [{roster_url}]({roster_url}); SHA-256 `{roster_hash}`.",
        f"Denominator: {len(roster)} teams × {expected_games_per_team} regular-season matches/team ÷ 2 = **{expected}**.",
        f"Pair archives: {len(pairs)} pages parsed; **{len(regular)}/{expected}** unique regular-season official game IDs.",
        f"Team-season archives: {len(team_ids)} pages parsed; **{dated_regular}/{len(regular)}** regular results dated by official game ID.",
        f"Other phases: {len(playoffs)} playoff and {len(playouts)} play-out results; denominators remain unknown.",
        f"Local match CSV SHA-256: `{csv_hash}`. Local per-page source inventory: `{source_report.name}`.", "",
        "## Official source page hashes", "",
        "| Type | Source URL | SHA-256 | Parsed rows |", "|---|---|---|---:|",
    ]
    for source in sorted(source_rows, key=lambda row: (str(row["page_type"]), str(row["source_url"]))):
        lines.append(f"| {source['page_type']} | {source['source_url']} | `{source['source_sha256']}` | {source['parsed_rows']} |")
    provenance_report.parent.mkdir(parents=True, exist_ok=True)
    provenance_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{season}: regular {len(regular)}/{expected}, exact-dated {dated_regular}/{len(regular)}, playoffs {len(playoffs)}, play-outs {len(playouts)}")
    return len(regular), dated_regular


def backfill(refresh: bool = False) -> tuple[int, int]:
    return backfill_season(SEASON, TOUR_ID, EXPECTED_TEAMS, EXPECTED_GAMES_PER_TEAM, refresh)


if __name__ == "__main__":
    backfill()
