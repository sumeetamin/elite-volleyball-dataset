"""Normalize completed match rows from the official Lega Volley calendar HTML."""
from __future__ import annotations

import csv
import hashlib
import re
from html import unescape
from pathlib import Path


FIELDS = ["source", "source_match_id", "competition_key", "competition", "sex", "season",
          "round", "match_date", "home_team", "away_team", "home_sets", "away_sets",
          "status", "source_url", "source_sha256"]


def import_superlega_page(source: Path, output: Path, coverage_path: Path,
                          season: str = "2024/25", source_url: str = "") -> int:
    raw = source.read_bytes()
    text = raw.decode("latin-1", errors="replace")
    digest = hashlib.sha256(raw).hexdigest()
    rows, current_round, current_date = [], "", ""
    # Giornata header identifies the round and a date, while match rows hold the
    # official stable IdGara plus home, set score, and away cells.
    for segment in re.split(r"(?=<tr\b)", text, flags=re.I):
        head = re.search(r"Giornata\s+([^<]+)", segment, re.I)
        if head:
            label = unescape(re.sub(r"\s+", " ", head.group(1))).strip()
            rm = re.search(r"(\d+)[^\w]*Giornata", label, re.I)
            dm = re.search(r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)\s+(20\d{2})", label)
            current_round = rm.group(1) if rm else label
            if dm:
                month_map = {"Gennaio":"01","Febbraio":"02","Marzo":"03","Aprile":"04","Maggio":"05","Giugno":"06","Luglio":"07","Agosto":"08","Settembre":"09","Ottobre":"10","Novembre":"11","Dicembre":"12"}
                current_date = f"{dm.group(3)}-{month_map.get(dm.group(2), '01')}-{int(dm.group(1)):02d}"
        if not re.search(r'class="DettaglioRisCal"', segment, re.I):
            continue
        cells = re.findall(r"<td\b([^>]*)>(.*?)</td>", segment, re.I | re.S)
        if len(cells) < 4:
            continue
        clean = lambda v: re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", unescape(v))).strip()
        number, home, score, away = [clean(cells[i][1]) for i in range(4)]
        idm = re.search(r"IdGara=(\d+)", segment)
        sm = re.fullmatch(r"(\d)\s*[-–]\s*(\d)", score)
        if not idm or not sm:
            continue
        rows.append({"source":"Lega Volley official calendar", "source_match_id":idm.group(1),
            "competition_key":"italy_superlega", "competition":"Italian SuperLega",
            "sex":"M", "season":season, "round":current_round, "match_date":current_date,
            "home_team":home, "away_team":away, "home_sets":int(sm.group(1)),
            "away_sets":int(sm.group(2)), "status":"completed",
            "source_url":source_url, "source_sha256":digest})
    unique = {r["source_match_id"]:r for r in rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(unique.values())
    with coverage_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["competition_key","competition","sex","season","expected_regular_season_matches","parsed_completed_matches","status","source_url","source_sha256"])
        w.writeheader();w.writerow({"competition_key":"italy_superlega","competition":"Italian SuperLega","sex":"M","season":season,"expected_regular_season_matches":132,"parsed_completed_matches":len(unique),"status":"partial_page_scope_return_leg_only" if len(unique)<132 else "regular_season_complete","source_url":source_url,"source_sha256":digest})
    return len(unique)


def merge_superlega_pages(sources: list[Path], output: Path, coverage_path: Path,
                          season: str = "2024/25", source_url: str = "") -> int:
    """Merge official first and return legs into unique match records."""
    all_rows = {}
    hashes = []
    for index, source in enumerate(sources):
        tmp = source.with_name(f".{source.stem}.normalized.tmp.csv")
        try:
            import_superlega_page(source, tmp, coverage_path, season, source_url)
            with tmp.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    all_rows[row["source_match_id"]] = row
            hashes.append(hashlib.sha256(source.read_bytes()).hexdigest())
        finally:
            tmp.unlink(missing_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        w.writerows(sorted(all_rows.values(), key=lambda r: (r["match_date"], int(r["source_match_id"]))))
    with coverage_path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["competition_key","competition","sex","season","expected_matches","observed_matches","coverage_pct","target_pct","target_met","status","source_urls","source_sha256"])
        w.writeheader();w.writerow({"competition_key":"italy_superlega","competition":"Italian SuperLega","sex":"M","season":season,"expected_matches":132,"observed_matches":len(all_rows),"coverage_pct":round(100*len(all_rows)/132,2),"target_pct":80,"target_met":"yes" if len(all_rows)/132>=.8 else "no","status":"regular_season_complete" if len(all_rows)>=132 else "partial","source_urls":source_url,"source_sha256":";".join(hashes)})
    return len(all_rows)
