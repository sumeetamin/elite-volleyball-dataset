import hashlib
import csv
import tempfile
import unittest
from pathlib import Path

from volleyball_dataset.import_cev import (
    import_leglist_page,
    merge_cev_matches,
    parse_leglist_page,
)


def match_row(match_id: int, match_number: str, sets_a: int = 3, sets_b: int = 1) -> str:
    return f'''<div id="ctl00_Content_Left_RADLIST_Matches_ctrl0_div_match">
<a href="MatchPage.aspx?mID={match_id}&amp;ID=70"></a>
<span id="x_LB_FederationMatchNumber">{match_number}</span>
<span id="x_Label2">Home {match_id}</span><span id="x_Label4">Away {match_id}</span>
<span id="x_LB_SetCasa">{sets_a}</span><span id="x_LB_SetOspiti">{sets_b}</span>
<span id="x_LB_DataOra">01/02/2001 18:00</span></div>'''


class CEVLegListTests(unittest.TestCase):
    def test_full_fixture_plus_final_four_merges_to_60_and_deduplicates(self):
        html = "\n".join(
            [match_row(1000 + i, f"L-{i + 1:03}") for i in range(48)]
            + [match_row(1048 + i, f"4-{i + 1:03}") for i in range(8)]
        )
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "leglist.html"
            source.write_text(html, encoding="utf-8")
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            full = parse_leglist_page(source, 70, "M", "2000/01 EUROPEAN CHAMPIONS LEAGUE")

        self.assertEqual(len(full), 56)
        self.assertEqual(sum(r["phase"] == "Main Phase" for r in full), 48)
        self.assertEqual(sum(r["phase"] == "4th Final" for r in full), 8)
        self.assertTrue(all(r["match_status"] == "completed" for r in full))
        self.assertTrue(all(r["source_sha256"] == source_hash for r in full))

        partial = [dict(r, phase="Main Phase", source_url="old-phase-page") for r in full[:8] + full[48:56]]
        final_four = [
            {**full[0], "match_id": f"CEV_{2000+i}", "source_record_id": str(2000+i),
             "source_match_number": f"F-{i+1:03}", "phase": "Final Four in Paris (FRA)",
             "source_url": "official-final-four-page"}
            for i in range(4)
        ]
        merged = merge_cev_matches(partial + final_four, full)
        self.assertEqual(len(merged), 60)
        self.assertEqual(sum(r["phase"] == "Main Phase" for r in merged), 48)
        self.assertEqual(sum(r["phase"] == "4th Final" for r in merged), 8)
        self.assertEqual(sum(r["phase"].startswith("Final Four") for r in merged), 4)
        self.assertEqual(next(r for r in merged if r["source_record_id"] == "1000")["source_url"].split("?")[0],
                         "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx")
        self.assertEqual(next(r for r in merged if r["source_record_id"] == "2000")["source_url"],
                         "official-final-four-page")

    def test_unknown_match_number_prefix_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "leglist.html"
            source.write_text(match_row(1, "X-001"), encoding="utf-8")
            rows = parse_leglist_page(source, 73, "W", "2000/01")
        self.assertEqual(rows[0]["phase"], "Unclassified (X)")

    def test_import_writes_provenance_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "leglist.html"
            source.write_text(match_row(1000, "L-001"), encoding="utf-8")
            silver = root / "silver"
            silver.mkdir()
            existing_path = silver / "cev_champions_league_matches.csv"
            with existing_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["match_id", "source_record_id", "competition_id", "gender", "sets_a", "sets_b", "season_name", "played_at_local", "phase", "source_url"])
                writer.writeheader()
                writer.writerow({"match_id": "CEV_1000", "source_record_id": "1000", "competition_id": "CEV_CL_M_70", "gender": "M", "sets_a": "3", "sets_b": "2", "season_name": "2000/01", "played_at_local": "01/02/2001", "phase": "old phase", "source_url": "old-url"})
                writer.writerow({"match_id": "CEV_2000", "source_record_id": "2000", "competition_id": "CEV_CL_M_70", "gender": "M", "sets_a": "3", "sets_b": "0", "season_name": "2000/01", "played_at_local": "02/02/2001", "phase": "Final Four", "source_url": "final-four-url"})
            coverage_path = root / "coverage_cev.csv"
            with coverage_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["gender", "season_id", "season_name", "phase", "parsed_matches", "status", "source_url", "sha256"])
                writer.writeheader()
                writer.writerow(dict(gender="M", season_id="70", season_name="2000/01", phase="overview", parsed_matches="0", status="ok", source_url="old-url", sha256="old"))
            source_url = "https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?CID=0&ID=70&PID=0&type=LegList"
            first = import_leglist_page(root, source, 70, "M", "2000/01", source_url)
            second = import_leglist_page(root, source, 70, "M", "2000/01", source_url)
            with existing_path.open(encoding="utf-8", newline="") as f:
                matches = list(csv.DictReader(f))
            with coverage_path.open(encoding="utf-8", newline="") as f:
                coverage = list(csv.DictReader(f))
        self.assertEqual(first[:2], (1, 2))
        self.assertEqual(second[:2], (1, 2))
        imported = next(r for r in matches if r["source_record_id"] == "1000")
        self.assertEqual(imported["source_url"], source_url)
        self.assertTrue(imported["source_sha256"])
        self.assertEqual(imported["phase"], "Main Phase")
        self.assertEqual(next(r for r in matches if r["source_record_id"] == "2000")["source_url"], "final-four-url")
        self.assertEqual(sum(r["phase"] == "complete_leglist" for r in coverage), 1)


if __name__ == "__main__":
    unittest.main()
