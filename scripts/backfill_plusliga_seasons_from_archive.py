"""Fetch and validate official PlusLiga regular-season results, 2014/15–2025/26.

The official season archive embeds all regular-season fixture cards (class RS)
and playoff cards separately. Bronze HTML hashes are retained per edition.
"""
from __future__ import annotations

import csv
import hashlib
import re
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TOURS = {
    "2014/15": 21, "2015/16": 23, "2016/17": 25, "2017/18": 27,
    "2018/19": 29, "2019/20": 32, "2020/21": 35, "2021/22": 38,
    "2022/23": 41, "2023/24": 44, "2024/25": 47, "2025/26": 52,
}
FIELDS = ["source", "source_match_id", "competition_key", "competition", "sex",
          "season", "phase", "match_date", "home_team", "away_team",
          "home_sets", "away_sets", "status", "source_url", "source_sha256"]


def scrape(season: str, tour: int) -> tuple[list[dict[str, str]], dict[str, str]]:
    url = f"https://www.tauronliga.pl/games/tour/{tour}/nocookies/1.html"
    response = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0 (compatible; dataset-research/1.0)"})
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    (ROOT / "data/bronze").mkdir(parents=True, exist_ok=True)
    (ROOT / f"data/bronze/plusliga_m_{season.replace('/', '_')}_official.html").write_bytes(response.content)
    soup = BeautifulSoup(response.content, "html.parser")
    cards = soup.select("section.filterable-content-RS[data-game-id]")
    if not cards:
        raise ValueError(f"No regular-season cards at {url}")
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for card in cards:
        gid = card.get("data-game-id", "").strip()
        if not gid or gid in seen:
            raise ValueError(f"Missing/duplicate official game ID in {season}: {gid!r}")
        seen.add(gid)
        box = card.select_one(".game-box") or card
        raw_date = box.select_one(".game-date > span")
        teams = box.select(".game-team")
        scores = box.select(".game-result .game-score")
        if not raw_date or len(teams) < 2:
            raise ValueError(f"Malformed official card {gid} in {season}")
        dm = re.search(r"(\d{2}\.\d{2}\.\d{4})", raw_date.get_text(" ", strip=True))
        d = None
        if dm:
            from datetime import datetime
            d = datetime.strptime(dm.group(1), "%d.%m.%Y").date()
        start = int(season[:4]); end = start + 1
        if d and not (date(start, 7, 1) <= d <= date(end, 6, 30)):
            raise ValueError(f"Out-of-season date {d} for {season}, game {gid}")
        home, away = [x.get_text(" ", strip=True) for x in teams[:2]]
        numeric = len(scores) == 2 and all(x.get_text(strip=True).isdigit() for x in scores)
        hs, aw = (int(scores[0].get_text(strip=True)), int(scores[1].get_text(strip=True))) if numeric else (None, None)
        # The official site uses 0:0 placeholders for postponed/cancelled fixtures.
        completed = numeric and (hs, aw) != (0, 0)
        if completed and (max(hs, aw) != 3 or min(hs, aw) not in {0, 1, 2}):
            raise ValueError(f"Invalid match score {hs}-{aw} for official game {gid}")
        rows.append({"source": "Official PLS PlusLiga archive", "source_match_id": gid,
                     "competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
                     "season": season, "phase": "regular_season", "match_date": d.isoformat() if d else "",
                     "home_team": home, "away_team": away,
                     "home_sets": str(hs) if completed else "", "away_sets": str(aw) if completed else "",
                     "status": "completed" if completed else "scheduled", "source_url": url,
                     "source_sha256": digest})
    return rows, {"url": url, "sha256": digest, "cards": str(len(rows)),
                  "completed": str(sum(r['status'] == 'completed' for r in rows)),
                  "dated": str(sum(bool(r['match_date']) for r in rows))}


def main() -> None:
    inv = []
    for season, tour in TOURS.items():
        rows, meta = scrape(season, tour)
        year = season.replace('/', '_')
        out = ROOT / f"data/silver/plusliga_m_{year}_matches.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(sorted(rows, key=lambda r: (r['match_date'], r['source_match_id'])))
        teams = {r['home_team'] for r in rows} | {r['away_team'] for r in rows}
        games_per_team = {t: sum(t in (r['home_team'], r['away_team']) for r in rows) for t in teams}
        balanced = len(set(games_per_team.values())) == 1
        # Some editions have withdrawals or abandoned fixtures (e.g. Stocznia
        # Szczecin in 2018/19), so the published schedule can be asymmetric.
        expected = len(rows)
        done = int(meta['completed'])
        cov = {"competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
               "season": season, "phase": "regular_season", "participating_teams": len(teams),
               "games_per_team": min(games_per_team.values()) if balanced else "variable", "expected_matches": expected,
               "observed_matches": done, "dated_matches": int(meta['dated']),
               "coverage_pct": round(100 * done / expected, 2), "date_coverage_pct": round(100 * int(meta['dated']) / expected, 2),
               "target_pct": 80, "target_met": "yes" if 100 * done / expected >= 80 else "no",
               "pair_pages_parsed": 0, "team_pages_parsed": 0, "standings_source_url": meta['url'],
               "standings_source_sha256": meta['sha256'],
               "denominator_method": "official season archive regular-season fixture IDs; participant GP cross-check " + ("balanced" if balanced else "asymmetric official schedule (withdrawal/fixture disposition requires review)")}
        with (ROOT / f"reports/plusliga_m_{year}_archive_coverage.csv").open("w", encoding="utf-8", newline="") as f:
            w=csv.DictWriter(f, fieldnames=list(cov)); w.writeheader(); w.writerow(cov)
        inv.append({"competition_key":"plusliga", "sex":"M", "season":season, **meta,
                    "regular_season_teams":len(teams), "games_per_team":";".join(f"{t}:{n}" for t,n in sorted(games_per_team.items()))})
        gp_summary = f"{len(teams)} teams x {next(iter(games_per_team.values()))} GP" if balanced else f"asymmetric GP ({min(games_per_team.values())}-{max(games_per_team.values())})"
        print(f"{season}: {done}/{expected}, {gp_summary}; sha256={meta['sha256']}", flush=True)
        time.sleep(0.4)
    with (ROOT / "reports/plusliga_archive_batch_inventory.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(inv[0])); w.writeheader(); w.writerows(inv)
    # Update scope denominators and audit from the same imported evidence.
    counts = {r["season"]: int(r["cards"]) for r in inv}
    sources = {r["season"]: r["url"] for r in inv}
    configs = list(csv.DictReader((ROOT / "config/competition_seasons.csv").open(encoding="utf-8-sig", newline="")))
    for r in configs:
        if r["competition_key"] == "plusliga" and r["sex"] == "M" and r["season"] in counts:
            r["expected_matches"] = str(counts[r["season"]])
            r["official_schedule_url"] = sources[r["season"]]
            r["notes"] = "Official PLS archive; regular-season fixture IDs and outcomes reconciled in reports/plusliga_archive_batch_inventory.csv; playoffs separate."
    with (ROOT / "config/competition_seasons.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(configs[0])); w.writeheader(); w.writerows(configs)
    ledger_path = ROOT / "reports/coverage_audit_current.csv"
    ledger = list(csv.DictReader(ledger_path.open(encoding="utf-8-sig", newline="")))
    for r in ledger:
        s=r["season"]
        if r["competition_key"] != "plusliga" or r["sex"] != "M" or s not in counts:
            continue
        matches = list(csv.DictReader((ROOT / f"data/silver/plusliga_m_{s.replace('/', '_')}_matches.csv").open(encoding="utf-8-sig", newline="")))
        observed = sum(m["status"] == "completed" for m in matches)
        expected = counts[s]
        r.update(expected_matches=str(expected), observed_matches=str(observed), observed_status="verified_official_archive",
                 coverage_pct=f"{100*observed/expected:.2f}", target_met="yes" if observed/expected >= .8 else "no",
                 denominator_status="verified", official_schedule_url=sources[s],
                 notes="Official PLS archive; official match IDs; date and outcome fields retained; regular season only.")
    with ledger_path.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(ledger[0])); w.writeheader(); w.writerows(ledger)


if __name__ == "__main__":
    main()
