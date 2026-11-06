"""Parse official PlusLiga/TAURON Liga team-comparison archive rows."""
from __future__ import annotations

import hashlib
import re
from html import unescape

FIELDS = ["source", "source_match_id", "competition_key", "competition", "sex", "season",
          "phase", "match_date", "home_team", "away_team", "home_sets", "away_sets",
          "status", "source_url", "source_sha256"]


def _text(markup: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", unescape(markup))).strip()


def parse_official_season_roster(payload: bytes) -> dict[str, dict[str, object]]:
    """Read final regular-season standings rows from an official tour page."""
    html = payload.decode("utf-8-sig", errors="replace")
    teams: dict[str, dict[str, object]] = {}
    for markup in re.findall(r"<tr\b[^>]*data-termin=['\"]1-1-18['\"][^>]*>.*?</tr>", html, flags=re.I | re.S):
        link = re.search(r"href=['\"]/teams/id/(\d+)/tour/\d+\.html['\"][^>]*class=['\"][^'\"]*table-teamname[^'\"]*['\"][^>]*>(.*?)</a>", markup, flags=re.I | re.S)
        if not link:
            continue
        cells = [_text(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", markup, flags=re.I | re.S)]
        # Final regular-season standings use cells [rank, team, points, played, wins, losses, ...].
        if len(cells) < 4 or not cells[3].isdigit():
            continue
        teams[link.group(1)] = {"team_name": _text(link.group(2)), "matches_played": int(cells[3])}
    if not teams:
        raise ValueError("Could not parse final regular-season team roster from official PlusLiga tour page")
    return teams


def parse_head_to_head_page(payload: bytes, source_url: str, competition_key: str,
                            season: str, sex: str) -> list[dict[str, object]]:
    """Parse match rows from one official all-time matchup comparison page."""
    raw_hash = hashlib.sha256(payload).hexdigest()
    html = payload.decode("utf-8-sig", errors="replace")
    rows: dict[str, dict[str, object]] = {}
    for markup in re.findall(r"<tr\b.*?</tr>", html, flags=re.I | re.S):
        match = re.search(r"<th\b[^>]*>\s*(20\d{2})\s*/\s*(20\d{2})\s*</th>", markup, flags=re.I | re.S)
        if not match or f"{match.group(1)}/{match.group(2)[-2:]}" != season:
            continue
        phase_match = re.search(r"<th\b[^>]*>\s*(Faza[^<]+)</th>", markup, flags=re.I | re.S)
        phase_text = _text(phase_match.group(1)) if phase_match else ""
        if "zasadnicz" in phase_text.casefold():
            phase = "regular_season"
        elif "play-out" in phase_text.casefold() or "playout" in phase_text.casefold():
            phase = "playouts"
        elif "play-off" in phase_text.casefold() or "playoff" in phase_text.casefold():
            phase = "playoffs"
        else:
            phase = phase_text

        cells = [_text(cell) for cell in re.findall(r"<(?:th|td)\b[^>]*>(.*?)</(?:th|td)>", markup, flags=re.I | re.S)]
        if len(cells) < 6:
            continue
        # Official comparison rows contain year, phase, home, separator, away,
        # score, and a match-report link. Team cells include an h6 element.
        team_cells = re.findall(r"<(?:td|th)\b[^>]*>\s*<h6\b[^>]*>(.*?)</h6>\s*</(?:td|th)>", markup, flags=re.I | re.S)
        if len(team_cells) < 2:
            continue
        home_team, away_team = (_text(team_cells[0]), _text(team_cells[1]))
        score_markup = re.search(r"<(?:td|th)\b[^>]*class=['\"][^'\"]*big[^'\"]*['\"][^>]*>(.*?)</(?:td|th)>", markup, flags=re.I | re.S)
        score_text = _text(score_markup.group(1)) if score_markup else ""
        score = re.search(r"\b([0-3])\s*:\s*([0-3])\b", score_text)
        if not score or max(map(int, score.groups())) != 3 or sum(map(int, score.groups())) not in (3, 4, 5):
            continue
        game = re.search(r"href=['\"][^'\"]*/games/id/(\d+)\.html", markup, flags=re.I)
        if not game:
            continue
        source_match_id = game.group(1)
        row = {"source": "official Polish league team-comparison archive",
               "source_match_id": source_match_id,
               "competition_key": competition_key,
               "competition": "Polish PlusLiga" if competition_key == "plusliga" else "Polish Tauron Liga",
               "sex": sex, "season": season, "phase": phase, "match_date": "",
               "home_team": home_team, "away_team": away_team,
               "home_sets": int(score.group(1)), "away_sets": int(score.group(2)),
               "status": "completed", "source_url": source_url, "source_sha256": raw_hash}
        old = rows.get(source_match_id)
        if old and (old["home_team"], old["away_team"], old["home_sets"], old["away_sets"]) != (home_team, away_team, row["home_sets"], row["away_sets"]):
            raise ValueError(f"Conflicting official comparison rows for game ID {source_match_id}")
        rows[source_match_id] = row
    return list(rows.values())
