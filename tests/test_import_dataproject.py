import tempfile
import unittest
from pathlib import Path

from volleyball_dataset.import_dataproject import parse_match_list


def match(match_id: int, section_id: int, leg_id: int, home_id: str,
          home: str, away_id: str, away: str, score: str) -> str:
    return f'''<div id="ctl00_Content_Main_{section_id}_userControl_RADLIST_Legs_ctrl{leg_id}_RADLIST_Matches_ctrl0_MatchRow">
<a href="MatchStatistics.aspx?mID={match_id}&amp;ID=45"></a>
<span id="x_LB_DataOra">01/11/2024 - 18:30</span>
<span id="x_{home_id}">{home}</span>
<span id="x_LB_SetCasa">{score.split('-')[0]}</span>
<span id="x_LB_SetOspiti">{score.split('-')[1]}</span>
<span id="x_{away_id}">{away}</span></div>'''


class DataProjectImportTests(unittest.TestCase):
    def test_alternate_team_ids_and_phase_are_preserved(self):
        page = "\n".join([
            match(1, 118, 0, "Label2", "Home A", "Label4", "Away A", "3-1"),
            match(2, 118, 2, "LBL_HomeTeamName", "Home B", "LBL_GuestTeamName", "Away B", "2-3"),
            match(4, 118, 42, "Label2", "Home D", "Label4", "Away D", "3-2"),
            match(3, 119, 0, "Label2", "Home C", "Label4", "Away C", "3-0"),
        ])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matches.html"
            source.write_text(page, encoding="utf-8")
            rows = parse_match_list(source, 45, "Superliga Masculina", "2024/25", "M")

        self.assertEqual(len(rows), 4)
        self.assertEqual([row["phase"] for row in rows], ["regular_season", "regular_season", "regular_season", "playoffs"])
        self.assertEqual([row["round"] for row in rows[:3]], ["round_1", "round_2", "round_22"])
        self.assertEqual(rows[1]["home_team"], "Home B")

    def test_scheduled_match_without_result_is_retained(self):
        page = match(4, 118, 1, "Label2", "Home D", "Label4", "Away D", "-")
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matches.html"
            source.write_text(page, encoding="utf-8")
            rows = parse_match_list(source, 45, "Superliga Masculina", "2024/25", "M")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["match_status"], "unknown")
        self.assertEqual(rows[0]["home_sets"], "")
        self.assertEqual(rows[0]["away_sets"], "")


if __name__ == "__main__":
    unittest.main()
