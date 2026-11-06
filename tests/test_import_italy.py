import csv
import tempfile
import unittest
from pathlib import Path

from volleyball_dataset.import_italy import merge_superlega_pages


def page(match_id: int, home: str, away: str, score: str) -> str:
    return f'''<tr><td>Giornata 1 - Domenica 29 Settembre 2024 Ore 18:00</td></tr>
<tr class="DettaglioRisCal" onclick="Tabellino.asp?IdGara={match_id}">
<td>1</td><td>{home}</td><td>{score}</td><td>{away}</td></tr>'''


class ItalyImportTests(unittest.TestCase):
    def test_merge_deduplicates_by_official_match_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.html"
            second = root / "second.html"
            first.write_text(page(100, "Home", "Away", "3-1"), encoding="latin-1")
            second.write_text(page(100, "Home", "Away", "3-1") + page(101, "Other", "Side", "0-3"), encoding="latin-1")
            output = root / "matches.csv"
            coverage = root / "coverage.csv"
            count = merge_superlega_pages([first, second], output, coverage)
            with output.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            with coverage.open(encoding="utf-8", newline="") as f:
                audit = next(csv.DictReader(f))
            self.assertEqual(count, 2)
            self.assertEqual({r["source_match_id"] for r in rows}, {"100", "101"})
            self.assertEqual(audit["observed_matches"], "2")
            self.assertEqual(audit["target_met"], "no")


if __name__ == "__main__":
    unittest.main()
