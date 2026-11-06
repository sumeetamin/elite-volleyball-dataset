import unittest

from scripts.backfill_italy_superlega_official import (
    discover_regular_season_id,
    official_fixture_ids,
    official_team_ids,
)


class ItalyHistoricalBackfillTests(unittest.TestCase):
    def test_discovers_the_official_a1_regular_season_id(self):
        page = b'''<html><title>Legavolley - Calendario 2000/2001</title>
        <select id="Campionato"><option value="93">Coppa Italia A1</option>
        <option value="100">Regular Season A1</option><option value="97">Play Off A1</option></select></html>'''
        season, competition_id = discover_regular_season_id(page)
        self.assertEqual(season, "2000/01")
        self.assertEqual(competition_id, "100")

    def test_fixture_census_counts_unique_ids_in_match_rows(self):
        page = b'''<table><tr class="DettaglioRisCal" onclick="Tabellino.asp?IdGara=11"><td>3-1</td></tr>
        <tr class="DettaglioCal" onclick="DettaglioGara.asp?IdGara=12"><td>scheduled</td></tr>
        <tr class="DettaglioRisCal" onclick="Tabellino.asp?IdGara=11"><td>duplicate</td></tr>
        <tr><td>unrelated IdGara=99</td></tr></table>'''
        self.assertEqual(official_fixture_ids(page), {"11", "12"})

    def test_team_census_reads_official_team_ids_from_schedule_cells(self):
        page = b'''<td class="DettaglioCal" onclick="DettaglioSquadra.asp?IdSquadra=20">A</td>
        <td class="DettaglioCal" onclick="DettaglioSquadra.asp?IdSquadra=21">B</td>
        <td class="Other" onclick="DettaglioSquadra.asp?IdSquadra=22">ignored</td>'''
        self.assertEqual(official_team_ids(page), {"20", "21"})


if __name__ == "__main__":
    unittest.main()
