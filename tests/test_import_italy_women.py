import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from backfill_italy_women_official import _parse_round  # noqa: E402


class ItalyWomenArchiveTests(unittest.TestCase):
    def test_dated_and_undated_completed_matches_remain_distinct(self):
        html = b"""
        <table class="risultati"><thead><tr><th>#123</th><th>04/11/2001</th></tr></thead>
        <tbody><tr><th class="num">3</th><td><a>Club A</a></td></tr>
        <tr><th class="num">1</th><td><a>Club B</a></td></tr></tbody></table>
        <table class="risultati"><thead><tr><th>#0</th><th>Venue only</th></tr></thead>
        <tbody><tr><th class="num">2</th><td><a>Club C</a></td></tr>
        <tr><th class="num">3</th><td><a>Club D</a></td></tr></tbody></table>
        """
        rows = _parse_round(html, "2001/02", "Round 1", "https://official.invalid", "sha")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["match_date"], "2001-11-04")
        self.assertEqual(rows[1]["match_date"], "")
        self.assertEqual(rows[1]["status"], "completed")
        self.assertNotEqual(rows[0]["source_match_id"], rows[1]["source_match_id"])

    def test_rejects_date_outside_named_season(self):
        html = b"""
        <table class="risultati"><thead><tr><th>#123</th><th>04/11/2000</th></tr></thead>
        <tbody><tr><th class="num">3</th><td><a>Club A</a></td></tr>
        <tr><th class="num">1</th><td><a>Club B</a></td></tr></tbody></table>
        """
        with self.assertRaisesRegex(ValueError, "outside named club season"):
            _parse_round(html, "2001/02", "Round 1", "https://official.invalid", "sha")


if __name__ == "__main__":
    unittest.main()
