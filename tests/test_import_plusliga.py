import csv
import tempfile
import unittest
from pathlib import Path

from volleyball_dataset.import_plusliga import import_plusliga_html


class PlusLigaImportTests(unittest.TestCase):
    def test_imports_both_pdf_outcome_encodings_and_preserves_unknown_date(self):
        html = '''<table id="e1">
<tr><td rowspan="8">13-09-2024</td><td rowspan="8">Kolejka nr 1</td><td>001<br>Hala</td><td>PGE GIEK SKRA Bełchatów</td><td>Team B</td><td>3 : 1</td><td>25:10</td>
</tr>
<tr><td>002</td><td>Arena</td><td>Team C</td><td>Team D</td><td>0</td><td>3</td><td>18:25</td>
</tr></table>'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output, coverage = root / "table.html", root / "matches.csv", root / "coverage.csv"
            source.write_text(html, encoding="utf-8")
            count = import_plusliga_html(source, output, coverage)
            with output.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            with coverage.open(encoding="utf-8", newline="") as f:
                audit = next(csv.DictReader(f))
        self.assertEqual(count, 2)
        self.assertEqual(rows[0]["home_team"], "PGE GiEK SKRA Bełchatów")
        self.assertEqual((rows[0]["home_sets"], rows[0]["away_sets"]), ("3", "1"))
        self.assertEqual(rows[1]["match_date"], "")
        self.assertEqual(audit["dated_matches"], "1")
        self.assertEqual(audit["target_met"], "no")


if __name__ == "__main__":
    unittest.main()
