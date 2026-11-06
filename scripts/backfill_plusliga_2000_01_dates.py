"""Join official PlusLiga 2000/01 team-season match dates to score IDs."""
from __future__ import annotations

import csv
import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "bronze"
ROSTER = RAW / "plusliga_m_2000_01_final_table.html"
MATCHES = ROOT / "data" / "silver" / "plusliga_m_2000_01_head_to_head.csv"
PAGE_REPORT = ROOT / "reports" / "plusliga_m_2000_01_team_date_sources.csv"
SEASON = "2000/2001"


def parse_team_page(payload: bytes, expected_season: str = SEASON) -> dict[str, str]:
    soup = BeautifulSoup(payload, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    match = re.search(r"Sezon\s+(20\d{2}/20\d{2})", title, re.IGNORECASE)
    if not match or match.group(1) != expected_season:
        raise ValueError(f"Expected PlusLiga {expected_season} page, got title {title!r}")
    dates: dict[str, tuple[str, str, str]] = {}
    for card in soup.select('div[id^="charttooltip"]'):
        id_match = re.fullmatch(r"charttooltip(\d+)", card.get("id", ""))
        date_node = card.select_one("p.date")
        if not id_match or not date_node:
            continue
        date_match = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", date_node.get_text(" ", strip=True))
        if not date_match:
            continue
        day, month, year = map(int, date_match.groups())
        date_value = datetime(year, month, day).date().isoformat()
        official_id = id_match.group(1)
        previous = dates.get(official_id)
        if previous and previous != date_value:
            raise ValueError(f"Conflicting official date for PlusLiga match {official_id}")
        dates[official_id] = date_value
    return dates


def _fetch_team(team_id: str) -> tuple[str, bytes, str, str, Path]:
    url = f"https://www.plusliga.pl/teams/id/{team_id}/tour/1/nocookies/1.html"
    cached = RAW / f"plusliga_m_2000_01_team_{team_id}_season.html"
    if cached.exists():
        payload = cached.read_bytes()
    else:
        request = Request(url, headers={"User-Agent": "EliteVolleyballDataset/0.1 (historical research)"})
        with urlopen(request, timeout=40) as response:
            payload = response.read()
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(payload)
        time.sleep(0.25)
    return team_id, payload, url, hashlib.sha256(payload).hexdigest(), cached


def backfill_dates() -> tuple[int, int]:
    from volleyball_dataset.import_polish_head_to_head import parse_official_season_roster

    roster = parse_official_season_roster(ROSTER.read_bytes())
    reports = []
    dates: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_fetch_team, team_id): team_id for team_id in roster}
        for future in as_completed(futures):
            team_id, payload, url, digest, cached_path = future.result()
            team_dates = parse_team_page(payload)
            reports.append({"season": "2000/01", "team_id": team_id,
                            "team_name": roster[team_id]["team_name"], "source_url": url,
                            "source_sha256": digest, "dated_match_cards": len(team_dates),
                            "retrieved_at_utc": datetime.fromtimestamp(
                                cached_path.stat().st_mtime, timezone.utc).isoformat()})
            for match_id, match_date in team_dates.items():
                previous = dates.get(match_id)
                if previous and previous[0] != match_date:
                    raise ValueError(f"Conflicting team-page dates for PlusLiga match {match_id}: {previous[0]} vs {match_date}")
                dates[match_id] = (match_date, url, digest)

    with MATCHES.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fields = list(rows[0]) if rows else []
    if "date_source_url" not in fields:
        fields.extend(["date_source_url", "date_source_sha256", "date_precision"])
    page_hashes = {row["source_url"]: row["source_sha256"] for row in reports}
    updated = 0
    for row in rows:
        date_record = dates.get(row["source_match_id"])
        if date_record:
            match_date, date_url, date_sha256 = date_record
            if row.get("match_date") and row["match_date"] != match_date:
                raise ValueError(f"Date conflict for official match {row['source_match_id']}")
            row["match_date"] = match_date
            row["date_source_url"] = date_url
            row["date_source_sha256"] = date_sha256
            row["date_precision"] = "official_day"
            updated += 1
        elif "date_source_url" in fields:
            row.setdefault("date_source_url", "")
            row.setdefault("date_source_sha256", "")
            row.setdefault("date_precision", "")

    MATCHES.parent.mkdir(parents=True, exist_ok=True)
    with MATCHES.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    PAGE_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with PAGE_REPORT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(reports[0]))
        writer.writeheader()
        writer.writerows(sorted(reports, key=lambda row: int(row["team_id"])))
    regular = [row for row in rows if row.get("phase") == "regular_season"]
    dated_regular = sum(bool(row.get("match_date")) for row in regular)
    print(f"Regular-season exact-date coverage: {dated_regular}/{len(regular)}; all phases dated: {updated}/{len(rows)}")
    return dated_regular, len(regular)


if __name__ == "__main__":
    backfill_dates()
