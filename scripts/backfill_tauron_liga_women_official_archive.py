"""Import women’s Tauron Liga regular-season cards from the official archive.

The official pages expose regular season (`RS`) separately from playoffs (`PO`).
Rows retain official match IDs and source-page hashes; 0:0 placeholders remain
scheduled, unscored fixtures. The index starts in 2008/09.
"""
from __future__ import annotations

import csv
import hashlib
import re
import time
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TOURS = {
    "2008/09": 10, "2009/10": 12, "2010/11": 14, "2011/12": 16,
    "2012/13": 18, "2013/14": 20, "2014/15": 22, "2015/16": 24,
    "2016/17": 26, "2017/18": 28, "2018/19": 30, "2019/20": 33,
    "2020/21": 36, "2021/22": 39, "2022/23": 42, "2023/24": 45,
    "2024/25": 48, "2025/26": 50,
}
BASE = "https://www.tauronligakobiet.pl"
FIELDS = ["source", "source_match_id", "competition_key", "competition", "sex", "season",
          "phase", "match_date", "home_team", "away_team", "home_sets", "away_sets",
          "status", "source_url", "source_sha256"]


def scrape(season: str, tour: int):
    url = f"{BASE}/games/tour/{tour}/nocookies/1.html"
    resp = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0 (compatible; dataset-research/1.0)"})
    resp.raise_for_status()
    raw = resp.content
    digest = hashlib.sha256(raw).hexdigest()
    bronze = ROOT / f"data/bronze/tauron_liga_w_{season.replace('/', '_')}_official.html"
    bronze.parent.mkdir(parents=True, exist_ok=True)
    bronze.write_bytes(raw)
    soup = BeautifulSoup(raw, "html.parser")
    cards = soup.select("section.filterable-content-RS[data-game-id]")
    if not cards:
        raise ValueError(f"Official index has no regular-season cards for {season}: {url}")
    rows, ids = [], set()
    for card in cards:
        game_id = card.get("data-game-id", "").strip()
        if not game_id or game_id in ids:
            raise ValueError(f"Blank/duplicate official ID in {season}: {game_id!r}")
        ids.add(game_id)
        box = card.select_one(".game-box") or card
        date_el = box.select_one(".game-date > span")
        teams = box.select(".game-team")
        score = box.select(".game-result .game-score")
        if not date_el or len(teams) < 2:
            raise ValueError(f"Malformed official match card {game_id} in {season}")
        match = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_el.get_text(" ", strip=True))
        played = datetime.strptime(match.group(1), "%d.%m.%Y").date() if match else None
        if played and not (date(int(season[:4]), 7, 1) <= played <= date(int(season[:4]) + 1, 6, 30)):
            raise ValueError(f"Date {played} outside season {season} for game {game_id}")
        home, away = (x.get_text(" ", strip=True) for x in teams[:2])
        numeric = len(score) == 2 and all(x.get_text(strip=True).isdigit() for x in score)
        hs, aw = (int(score[0].get_text(strip=True)), int(score[1].get_text(strip=True))) if numeric else (None, None)
        completed = numeric and (hs, aw) != (0, 0)
        if completed and (max(hs, aw) != 3 or min(hs, aw) not in {0, 1, 2}):
            raise ValueError(f"Invalid set result {hs}-{aw} for {season} game {game_id}")
        rows.append({"source": "Official Tauron Liga Kobiet archive", "source_match_id": game_id,
                     "competition_key": "tauron_liga", "competition": "Polish Tauron Liga", "sex": "F",
                     "season": season, "phase": "regular_season", "match_date": played.isoformat() if played else "",
                     "home_team": home, "away_team": away, "home_sets": str(hs) if completed else "",
                     "away_sets": str(aw) if completed else "", "status": "completed" if completed else "scheduled",
                     "source_url": url, "source_sha256": digest})
    return rows, url, digest


def main():
    inventory = []
    for season, tour in TOURS.items():
        rows, url, digest = scrape(season, tour)
        teams = {r["home_team"] for r in rows} | {r["away_team"] for r in rows}
        gp = Counter(t for r in rows for t in (r["home_team"], r["away_team"]))
        exp, done = len(rows), sum(r["status"] == "completed" for r in rows)
        year = season.replace("/", "_")
        dest = ROOT / f"data/silver/tauron_liga_w_{year}_matches.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(sorted(rows, key=lambda r:(r["match_date"],r["source_match_id"])))
        coverage = {"competition_key":"tauron_liga", "competition":"Polish Tauron Liga", "sex":"F", "season":season,
                    "phase":"regular_season", "participating_teams":len(teams),
                    "games_per_team":str(min(gp.values())) if len(set(gp.values())) == 1 else "variable",
                    "expected_matches":exp, "observed_matches":done,
                    "dated_matches":sum(bool(r["match_date"]) for r in rows),
                    "coverage_pct":round(100*done/exp,2),
                    "date_coverage_pct":round(100*sum(bool(r["match_date"]) for r in rows)/exp,2),
                    "target_pct":80, "target_met":"yes" if done/exp >= .8 else "no",
                    "pair_pages_parsed":0, "team_pages_parsed":0, "standings_source_url":url,
                    "standings_source_sha256":digest,
                    "denominator_method":"official season archive regular-season match IDs; unique ID count cross-checked against participant GP"}
        with (ROOT/f"reports/tauron_liga_w_{year}_archive_coverage.csv").open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(coverage));w.writeheader();w.writerow(coverage)
        inventory.append({"season":season,"tour_id":tour,"source_url":url,"source_sha256":digest,
                          "regular_season_fixtures":exp,"completed_results":done,"dated_fixtures":coverage["dated_matches"],
                          "participating_teams":len(teams),"games_per_team":";".join(f"{k}:{gp[k]}" for k in sorted(gp))})
        print(f"{season}: {done}/{exp}; dates={coverage['dated_matches']}; teams={len(teams)}; sha256={digest}",flush=True)
        time.sleep(.25)
    with (ROOT/"reports/tauron_liga_w_archive_batch_inventory.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(inventory[0]));w.writeheader();w.writerows(inventory)


if __name__ == "__main__":
    main()
