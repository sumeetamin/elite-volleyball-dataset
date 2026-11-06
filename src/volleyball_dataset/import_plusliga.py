"""Normalize match outcomes from an extracted official PlusLiga season PDF table.

The archived source text is an HTML table transcription of the official PDF;
the original PDF remains the primary source and its hash is recorded separately.
"""
from __future__ import annotations

import csv
import hashlib
import re
from html import unescape
from pathlib import Path


FIELDS = ["source", "source_match_id", "competition_key", "competition", "sex", "season",
          "round", "match_date", "home_team", "away_team", "home_sets", "away_sets",
          "status", "source_url", "source_sha256", "upstream_pdf_sha256"]

TEAM_ALIASES = {"PGE GIEK SKRA Bełchatów": "PGE GiEK SKRA Bełchatów"}


def _clean(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", unescape(value))
    return re.sub(r"\s+", " ", value).strip()


def import_plusliga_html(source: Path, output: Path, coverage_path: Path,
                         season: str = "2024/25", source_url: str = "",
                         upstream_pdf_sha256: str = "", expected_matches: int = 240) -> int:
    raw = source.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    transcript_hash = hashlib.sha256(raw).hexdigest()
    found: dict[str, dict] = {}

    for tr in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", text, re.I | re.S):
        cells = [_clean(x) for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr.group(1), re.I | re.S)]
        if len(cells) < 5:
            continue
        # Result cells occur as "3 : 1" or, in some PDF text layers, as two
        # neighboring digit cells "3", "1". Set-point cells are always 2-digit
        # values around a colon, so they cannot satisfy this outcome pattern.
        result_index = next((i for i, cell in enumerate(cells) if re.fullmatch(r"\d\s*[: ]\s*\d", cell)), -1)
        if result_index >= 2:
            result = re.fullmatch(r"(\d)\s*[: ]\s*(\d)", cells[result_index])
            home_sets, away_sets = map(int, result.groups())
            metadata = cells[:result_index - 2]
        else:
            result_index = -1
            for i in range(2, len(cells) - 2):
                if re.fullmatch(r"\d", cells[i]) and re.fullmatch(r"\d", cells[i + 1]) and re.fullmatch(r"\d{1,2}:\d{1,2}", cells[i + 2]):
                    result_index = i
                    home_sets, away_sets = int(cells[i]), int(cells[i + 1])
                    break
            if result_index < 2:
                continue
            metadata = cells[:result_index - 2]

        home_team, away_team = cells[result_index - 2], cells[result_index - 1]
        date_match = re.search(r"\b(\d{2})-(\d{2})-(20\d{2})\b", " ".join(metadata))
        match_date = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}" if date_match else ""

        # Prefer a dedicated three-digit match-number cell. If the first row of
        # a round combines date, number and venue, take the first plausible ID
        # in reading order (before venue street numbers such as 122).
        exact_id = next((cell for cell in metadata if re.fullmatch(r"\d{3}", cell) and 1 <= int(cell) <= expected_matches), "")
        tokens = re.findall(r"(?<!\d)(\d{3})(?!\d)", " ".join(metadata))
        source_match_id = exact_id or next((token for token in tokens if 1 <= int(token) <= expected_matches), "")
        if not source_match_id or not home_team or not away_team or home_team.isdigit() or away_team.isdigit():
            continue
        if home_sets + away_sets not in (3, 4, 5) or max(home_sets, away_sets) != 3:
            continue
        row = {"source": "PlusLiga official season schedule PDF",
               "source_match_id": source_match_id.zfill(3), "competition_key": "plusliga",
               "competition": "Polish PlusLiga", "sex": "M", "season": season,
               "round": "", "match_date": match_date,
               "home_team": TEAM_ALIASES.get(home_team, home_team),
               "away_team": TEAM_ALIASES.get(away_team, away_team),
               "home_team_source": home_team, "away_team_source": away_team,
               "home_sets": home_sets, "away_sets": away_sets, "status": "completed",
               "source_url": source_url, "source_sha256": transcript_hash,
               "upstream_pdf_sha256": upstream_pdf_sha256}
        previous = found.get(row["source_match_id"])
        if previous and (previous["home_team"], previous["away_team"], previous["home_sets"], previous["away_sets"]) != (row["home_team"], row["away_team"], home_sets, away_sets):
            raise ValueError(f"Conflicting duplicate PlusLiga match ID {row['source_match_id']}")
        found[row["source_match_id"]] = row

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS + ["home_team_source", "away_team_source"])
        writer.writeheader()
        writer.writerows(sorted(found.values(), key=lambda r: r["source_match_id"]))

    dated = sum(bool(row["match_date"]) for row in found.values())
    with coverage_path.open("w", newline="", encoding="utf-8") as f:
        fields = ["competition_key", "competition", "sex", "season", "expected_matches",
                  "observed_matches", "coverage_pct", "target_pct", "target_met", "dated_matches",
                  "date_coverage_pct", "status", "source_url", "source_sha256", "upstream_pdf_sha256"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"competition_key": "plusliga", "competition": "Polish PlusLiga", "sex": "M",
            "season": season, "expected_matches": expected_matches, "observed_matches": len(found),
            "coverage_pct": round(100 * len(found) / expected_matches, 2) if expected_matches else "",
            "target_pct": 80, "target_met": "yes" if expected_matches and len(found) / expected_matches >= .8 else "no",
            "dated_matches": dated, "date_coverage_pct": round(100 * dated / len(found), 2) if found else 0,
            "status": "regular_season_complete" if len(found) >= expected_matches else "partial",
            "source_url": source_url, "source_sha256": transcript_hash,
            "upstream_pdf_sha256": upstream_pdf_sha256})
    return len(found)
