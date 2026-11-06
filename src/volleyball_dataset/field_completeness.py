"""Report field-level coverage without treating absent columns as zero observations."""
from __future__ import annotations

import csv
import re
from pathlib import Path


_PATTERNS = {
    "stable_match_id": re.compile(r"^(source_match_id|match_id|id_gara)$", re.I),
    "match_date": re.compile(r"^(match_date|played_at_local|scheduled_at_utc)$", re.I),
    "team_names": re.compile(r"^(home_team|away_team|team_a|team_b|team_a_name|team_b_name)$", re.I),
    "match_result": re.compile(r"^(home_sets|away_sets|sets_a|sets_b)$", re.I),
    "set_points": re.compile(r"^(set[_ ]?[1-5].*(home|guest|away)|set[1-5](home|guest))", re.I),
    "box_score_stats": re.compile(r"(ace|block|attack|reception|serve_error|service_error|dig|kill)", re.I),
    "rally_data": re.compile(r"(rally|point_winner|serving_team|rally_number)", re.I),
    "rotation_data": re.compile(r"(rotation|setter_position)", re.I),
    "lineup_data": re.compile(r"(lineup|starting_player|player_id|roster)", re.I),
    "odds_data": re.compile(r"(odds|bookmaker|decimal_price|market_line)", re.I),
    "official_scoresheet_link": re.compile(r"^scoresheet_url$", re.I),
    "official_match_report_link": re.compile(r"^match_report_url$", re.I),
    "official_libero_report_link": re.compile(r"^libero_report_url$", re.I),
    "official_video_challenge_report_link": re.compile(r"^video_challenge_report_url$", re.I),
}


def audit_table(path: Path) -> list[dict[str, object]]:
    """Measure available fields by competition/sex/season within one CSV table."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        records = list(reader)
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in records:
        key = (row.get("competition_key", "unknown") or "unknown",
               row.get("sex", row.get("gender", "unknown")) or "unknown",
               row.get("season", row.get("season_name", "unknown")) or "unknown")
        groups.setdefault(key, []).append(row)
    result: list[dict[str, object]] = []
    for (competition, sex, season), rows in sorted(groups.items()):
        for category, pattern in _PATTERNS.items():
            fields = [column for column in columns if pattern.search(column)]
            available = bool(fields)
            if category == "match_result" and available:
                count = 0
                for row in rows:
                    try:
                        a = int(row.get("home_sets", row.get("sets_a", "")))
                        b = int(row.get("away_sets", row.get("sets_b", "")))
                    except (TypeError, ValueError):
                        continue
                    status = (row.get("match_status") or row.get("status") or "completed").casefold()
                    count += int(status in {"completed", "closed", "finished", "result is official", "corrected"}
                                  and max(a, b) == 3 and min(a, b) in (0, 1, 2))
            elif available:
                count = sum(any(str(row.get(field, "")).strip() for field in fields) for row in rows)
            else:
                count = None
            result.append({
                "source_file": path.name, "competition_key": competition, "sex": sex,
                "season": season, "table_rows": len(rows), "field_group": category,
                "available_columns": ";".join(fields), "rows_with_data": count,
                "coverage_pct": round(100 * count / len(rows), 4) if count is not None and rows else "",
                "availability": "measured" if available else "not_in_imported_schema",
                "measurement": ("valid completed 3-0 through 3-2 results" if category == "match_result"
                                else "row has at least one non-empty field in group" if available else ""),
            })
    return result


def build_field_audit(paths: list[Path]) -> list[dict[str, object]]:
    rows = []
    for path in paths:
        rows.extend(audit_table(path))
    return rows
