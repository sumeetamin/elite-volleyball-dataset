import csv
import importlib.util
from datetime import date, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_plusliga_2012_13_browser_capture.py"
spec = importlib.util.spec_from_file_location("plusliga_2012_13_capture", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_capture_validation_generates_stable_derived_match_keys(tmp_path):
    teams = [f"Team {i}" for i in range(10)]
    rotation = list(range(10))
    rows = []
    for round_number in range(18):
        day = date(2012, 9, 1) + timedelta(days=round_number)
        for i in range(5):
            a, b = rotation[i], rotation[9 - i]
            if round_number >= 9:
                a, b = b, a
            rows.append({
                "match_date": day.strftime("%d.%m.%Y"), "phase": "Faza Zasadnicza",
                "home_team": teams[a], "home_sets": 3, "away_sets": 1, "away_team": teams[b],
            })
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    capture = tmp_path / "capture.tsv"
    with capture.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(rows)

    first, digest = module.normalize_capture(capture)
    second, _ = module.normalize_capture(capture)
    assert len(first) == 90
    assert len({row["source_match_id"] for row in first}) == 90
    assert {row["source_match_id"] for row in first} == {row["source_match_id"] for row in second}
    assert all(row["source_match_id"].startswith("derived-sha256:") for row in first)
    assert digest == module.hashlib.sha256(capture.read_bytes()).hexdigest()

