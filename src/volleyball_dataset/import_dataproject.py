"""Import official Data Project competition match-list pages.

Raw HTML is kept as an immutable source artifact; this module normalizes one
record per provider match ID and deliberately does not infer team point stats.
"""
from __future__ import annotations

import hashlib
import re
import csv
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE = "CBV Data Project"
BASE = "https://cbv-web.dataproject.com"
FIELDS = [
    "source", "source_match_id", "competition", "season", "sex", "competition_key",
    "phase", "round", "match_date", "home_team", "away_team", "home_sets", "away_sets", "match_status",
    "source_url", "source_sha256",
]


def parse_match_list(path: Path, competition_id: int, competition: str,
                     season: str, sex: str) -> list[dict]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    rows: dict[str, dict] = {}
    source = payload.decode("utf-8", errors="replace")
    row_starts = list(re.finditer(
        r'<div id="(?P<section>[^" ]*Content_Main_(?P<section_id>\d+)_userControl_RADLIST_Legs_ctrl(?P<leg>\d+)[^" ]*_MatchRow)"',
        source,
    ))
    first_section = None
    for row_match, next_match in zip(row_starts, row_starts[1:] + [None]):
        start = row_match.start()
        end = next_match.start() if next_match else len(source)
        block = source[start:end]
        match = re.search(r"MatchStatistics\.aspx\?mID=(\d+)", block)
        if not match: continue
        match_id = match.group(1)
        section_id = row_match.group("section_id")
        if first_section is None and section_id:
            first_section = section_id
        phase = "regular_season" if section_id and section_id == first_section else "playoffs" if section_id else "unknown"
        leg_index = int(row_match.group("leg"))
        if phase == "regular_season" and leg_index >= 0:
            # The archived pages use child indexes 0, 2, ..., 42 for rounds 1–22.
            # Index 1, 3, etc. may occur in synthetic fixtures, so integer division
            # correctly maps both child slots to the same numbered round.
            round_label = f"round_{leg_index // 2 + 1}"
        else:
            round_label = ""
        def span(*suffixes: str) -> str | None:
            for suffix in suffixes:
                m = re.search(r'<span[^>]*id="[^"]*_' + re.escape(suffix) + r'"[^>]*>(.*?)</span>', block, re.S)
                if m:
                    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", m.group(1))).strip()
            return None
        date_text = span("LB_DataOra")
        home = span("Label2", "LBL_HomeTeamName")
        away = span("Label4", "LBL_GuestTeamName")
        hs, aws = span("LB_SetCasa"), span("LB_SetOspiti")
        if not (date_text and home and away):
            continue
        date_text = re.sub(r"\s+", " ", date_text).replace(" - ", " ")
        parsed_date = None
        for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(date_text, fmt).date().isoformat()
                break
            except ValueError:
                pass
        if not parsed_date:
            continue
        rows[match_id] = {
            "source": SOURCE,
            "source_match_id": match_id,
            "competition": competition,
            "season": season,
            "sex": sex,
            "competition_key": "brazil_superliga",
            "phase": phase,
            "round": round_label,
            "match_date": parsed_date,
            "home_team": home,
            "away_team": away,
            "home_sets": int(hs) if hs and hs.isdigit() else "",
            "away_sets": int(aws) if aws and aws.isdigit() else "",
            "match_status": "completed" if hs and aws and max(int(hs), int(aws)) == 3 and min(int(hs), int(aws)) <= 2 else "unknown",
            "source_url": f"{BASE}/CompetitionMatches.aspx?ID={competition_id}",
            "source_sha256": digest,
        }
    return list(rows.values())


def import_directory(source_dir: Path, output: Path, coverage_path: Path) -> tuple[int, int]:
    season_map = {
        "2": ("2017/18", "M", "Superliga Masculina"),
        "3": ("2017/18", "F", "Superliga Feminina"),
        "5": ("2018/19", "M", "Superliga Masculina"),
        "6": ("2018/19", "F", "Superliga Feminina"),
        "8": ("2019/20", "M", "Superliga Masculina"),
        "9": ("2019/20", "F", "Superliga Feminina"),
        "11": ("2020/21", "M", "Superliga Masculina"),
        "12": ("2020/21", "F", "Superliga Feminina"),
        "13": ("2021/22", "M", "Superliga Masculina"),
        "14": ("2021/22", "F", "Superliga Feminina"),
        "17": ("2022/23", "M", "Superliga Masculina"),
        "18": ("2022/23", "F", "Superliga Feminina"),
        "27": ("2023/24", "M", "Superliga Masculina"),
        "28": ("2023/24", "F", "Superliga Feminina"),
        "45": ("2024/25", "M", "Superliga Masculina"),
        "46": ("2024/25", "F", "Superliga Feminina"),
    }
    records, coverage = [], []
    for path in sorted(source_dir.glob("cbv_*_matches.html")):
        match = re.search(r"cbv_[mf]_(\d+)_matches\.html$", path.name)
        if not match or match.group(1) not in season_map:
            continue
        cid = match.group(1)
        season, sex, competition = season_map[cid]
        rows = parse_match_list(path, int(cid), competition, season, sex)
        for row in rows:
            row["source_match_id"] = f"{cid}:{row['source_match_id']}"
        records.extend(rows)
        regular = [r for r in rows if r["phase"] == "regular_season"]
        regular_completed = [r for r in regular if r["match_status"] == "completed"]
        # The denominator is the number of unique regular-phase official match IDs
        # in this season's preserved source page (not a presumed league format).
        expected = len(regular) if regular else None
        coverage.append({
            "source": SOURCE, "competition": competition, "sex": sex,
            "season": season, "competition_id": int(cid),
            "match_records": len(rows), "parsed_regular_rows": len(regular),
            "expected_regular_matches": expected or "",
            "completed_regular_matches": len(regular_completed),
            "regular_coverage_pct": round(100 * len(regular_completed) / expected, 2) if expected else "",
            "status": "retrieved" if rows else "no_parseable_rows",
            "source_url": f"{BASE}/CompetitionMatches.aspx?ID={cid}",
            "raw_file": path.as_posix(),
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    coverage_path.parent.mkdir(parents=True, exist_ok=True)
    unique = {(r["source"], r["source_match_id"]): r for r in records}
    ordered = sorted(unique.values(), key=lambda r: (r["match_date"], r["competition"], r["source_match_id"]))
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS); writer.writeheader(); writer.writerows(ordered)
    cov_fields = list(coverage[0]) if coverage else ["source", "competition", "sex", "season", "competition_id", "match_records", "parsed_regular_rows", "expected_regular_matches", "completed_regular_matches", "regular_coverage_pct", "status", "source_url", "raw_file", "source_sha256"]
    with coverage_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cov_fields); writer.writeheader(); writer.writerows(coverage)
    return len(ordered), len(coverage)


def download_archives(source_dir: Path, ids: list[int] | None = None) -> int:
    """Download official CBV first-division archives for seasons identified in the index."""
    from time import sleep
    source_dir.mkdir(parents=True, exist_ok=True)
    index_path = source_dir / "cbv_mainhome.html"
    if not index_path.exists():
        payload = urlopen(Request(f"{BASE}/MainHome.aspx", headers={"User-Agent": "volleyball-dataset research contact"}), timeout=40).read()
        index_path.write_bytes(payload)
    index = index_path.read_text(encoding="utf-8", errors="replace")
    found = {}
    for href, cid, label in re.findall(r'href="([^"]*CompetitionHome\.aspx\?ID=(\d+)[^"]*)"[^>]*>(.*?)</a>', index, re.I | re.S):
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", unescape(label))).strip()
        season_match = re.search(r"(20\d{2})/(20\d{2})", title)
        sex = "M" if re.search(r"Masculina", title, re.I) else "F" if re.search(r"Feminina", title, re.I) else None
        if "Superliga" in title and sex:
            season = f"{season_match.group(1)[2:]}/{season_match.group(2)[2:]}" if season_match else None
            # Older archive labels omit years; category headers immediately before
            # them identify the season, so map known IDs from the official index.
            legacy = {"11": "2020/21", "12": "2020/21", "8": "2019/20", "9": "2019/20",
                      "5": "2018/19", "6": "2018/19", "2": "2017/18", "3": "2017/18"}
            season = season or legacy.get(cid)
            if season:
                found[int(cid)] = (season, sex)
    wanted = set(ids) if ids else set(found)
    downloaded = 0
    for cid in sorted(wanted & found.keys()):
        target = source_dir / f"cbv_{found[cid][1].lower()}_{cid}_matches.html"
        if target.exists() and target.stat().st_size > 1000:
            continue
        url = f"{BASE}/CompetitionMatches.aspx?ID={cid}"
        payload = urlopen(Request(url, headers={"User-Agent": "volleyball-dataset research contact"}), timeout=60).read()
        if b"MatchStatistics.aspx?mID=" not in payload:
            raise ValueError(f"Official competition page {cid} returned no match rows")
        target.write_bytes(payload)
        downloaded += 1
        sleep(.3)
    return downloaded
