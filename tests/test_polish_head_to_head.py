import unittest

from volleyball_dataset.import_polish_head_to_head import parse_head_to_head_page, parse_official_season_roster


class PolishHeadToHeadImportTests(unittest.TestCase):
    def test_extracts_completed_match_and_filters_to_requested_season(self):
        page = b'''<table>
        <tr><th>2000 / 2001</th><th>Faza Zasadnicza</th>
          <td><h6>KS CITROEN NYSA</h6></td><td>-</td><td><h6>INDYKPOL AZS OLSZTYN</h6></td>
          <td class="big"><span class="number win">3</span><span>:</span><span class="number lost">2</span></td>
          <td><a href="/games/id/1000080.html">More</a></td></tr>
        <tr><th>2001 / 2002</th><th>Faza Zasadnicza</th>
          <td><h6>Other</h6></td><td>-</td><td><h6>Side</h6></td>
          <td class="big"><span class="number win">3</span><span>:</span><span class="number lost">0</span></td>
          <td><a href="/games/id/1000172.html">More</a></td></tr>
        <tr><th>2000 / 2001</th><th>Faza Play-Out</th>
          <td><h6>Team X</h6></td><td>-</td><td><h6>Team Y</h6></td>
          <td class="big"><span class="number win">3</span><span>:</span><span class="number lost">1</span></td>
          <td><a href="/games/id/1000188.html">More</a></td></tr></table>'''
        rows = parse_head_to_head_page(page, "https://www.plusliga.pl/test", "plusliga", "2000/01", "M")
        self.assertEqual(len(rows), 2)
        row = next(item for item in rows if item["source_match_id"] == "1000080")
        self.assertEqual(row["source_match_id"], "1000080")
        self.assertEqual((row["home_team"], row["away_team"]), ("KS CITROEN NYSA", "INDYKPOL AZS OLSZTYN"))
        self.assertEqual((row["home_sets"], row["away_sets"]), (3, 2))
        self.assertEqual(row["phase"], "regular_season")
        self.assertTrue(row["source_sha256"])
        playout = next(item for item in rows if item["source_match_id"] == "1000188")
        self.assertEqual(playout["phase"], "playouts")

    def test_roster_comes_from_official_final_regular_season_standings(self):
        page = b'''<tr data-termin="1-1-18"><td>1</td><td><a href="/teams/id/21/tour/1.html" class="table-teamname">TEAM A</a></td><td>32</td><td>18</td></tr>
        <tr data-termin="1-1-18"><td>2</td><td><a href="/teams/id/24/tour/1.html" class="table-teamname">TEAM B</a></td><td>29</td><td>18</td></tr>
        <tr data-termin="1-1-2"><td>1</td><td><a href="/teams/id/99/tour/1.html" class="table-teamname">WRONG ROUND</a></td><td>4</td><td>2</td></tr>'''
        roster = parse_official_season_roster(page)
        self.assertEqual(set(roster), {"21", "24"})
        self.assertEqual({x["matches_played"] for x in roster.values()}, {18})


if __name__ == "__main__":
    unittest.main()
