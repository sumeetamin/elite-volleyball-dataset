import csv
import unittest
from pathlib import Path
from volleyball_dataset.coverage_audit import _canonical_cev_season


ROOT = Path(__file__).resolve().parents[1]


class HistoricalScopeInventoryTests(unittest.TestCase):
    def test_ceV_final_calendar_year_maps_to_previous_club_season(self):
        self.assertEqual(_canonical_cev_season("2012 CEV Volleyball Champions League - Men"), "2011/12")
        self.assertEqual(_canonical_cev_season("CEV XTB Champions League Volley 2027 | Men"), "2026/27")
        self.assertIsNone(_canonical_cev_season("2012 CEV Volleyball Cup"))

    def test_inventory_covers_each_competition_lineage_through_current_season(self):
        with (ROOT / "config" / "competition_seasons.csv").open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        keys = [(r["competition_key"], r["sex"], r["season"]) for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(rows), 274)
        counts = {}
        for row in rows:
            key = (row["competition_key"], row["sex"])
            counts[key] = counts.get(key, 0) + 1
        expected = {
            ("italy_superlega", "M"): 28,
            ("italy_serie_a1_women", "F"): 28,
            ("plusliga", "M"): 27,
            ("tauron_liga", "F"): 27,
            ("brazil_superliga", "M"): 28,
            ("brazil_superliga", "F"): 28,
            ("cev_cl", "M"): 27,
            ("cev_cl", "F"): 27,
            ("vnl", "M"): 27,
            ("vnl", "F"): 27,
        }
        self.assertEqual(counts, expected)
        self.assertEqual(sum(bool(r["expected_matches"].strip()) for r in rows), 31)
        cev_2000 = {(r["sex"], r["expected_matches"]) for r in rows
                    if r["competition_key"] == "cev_cl" and r["season"] == "2000/01"}
        self.assertEqual(cev_2000, {("M", "60"), ("F", "60")})
        cancelled_vnl_2020 = {(r["sex"], "cancelled" if "season_status=cancelled" in r["notes"] else "", r["expected_matches"])
                              for r in rows if r["competition_key"] == "vnl" and r["season"] == "VNL 2020"}
        self.assertEqual(cancelled_vnl_2020, {("M", "cancelled", ""), ("F", "cancelled", "")})
        vnl_2021 = {(r["sex"], r["expected_matches"]) for r in rows
                    if r["competition_key"] == "vnl" and r["season"] == "VNL 2021"}
        self.assertEqual(vnl_2021, {("M", "124"), ("F", "124")})
        fivb_legacy = [r for r in rows if r["competition_key"] == "vnl"
                       and (r["season"].startswith("World League ") or r["season"].startswith("World Grand Prix "))
                       and r["season"].rsplit(" ", 1)[-1] in {"2000", "2001", "2002", "2003", "2004", "2005"}]
        self.assertEqual(len(fivb_legacy), 12)
        self.assertEqual(sum("fivb_archive_status=not_listed" in r["notes"] for r in fivb_legacy), 10)
        self.assertEqual(sum("fivb_archive_status=listed_unmanaged" in r["notes"] for r in fivb_legacy), 2)
        self.assertEqual(sum(r["season"] == "1999/2000" for r in rows), 4)


if __name__ == "__main__":
    unittest.main()
