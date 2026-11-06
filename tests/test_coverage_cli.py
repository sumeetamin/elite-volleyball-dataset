import csv
from pathlib import Path

from volleyball_dataset.cli import main


def test_coverage_cli_keeps_denominator_without_fabricating_result_coverage(tmp_path, monkeypatch, capsys):
    inventory = tmp_path / "inventory.csv"
    with inventory.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "competition_key", "competition", "sex", "season", "expected_matches", "target_pct"
        ])
        writer.writeheader()
        writer.writerow({
            "competition_key": "brazil_superliga", "competition": "Brazil Superliga",
            "sex": "M", "season": "2016/17", "expected_matches": "132", "target_pct": "80",
        })
    output = tmp_path / "audit.csv"
    monkeypatch.setattr("sys.argv", [
        "volley-data", "coverage", "--inventory", str(inventory),
        "--data-dir", str(tmp_path / "data"), "--output", str(output),
    ])

    main()

    result = next(csv.DictReader(output.open(encoding="utf-8")))
    assert result["expected_matches"] == "132"
    assert result["denominator_status"] == "verified"
    assert result["observed_matches"] == ""
    assert result["coverage_pct"] == ""
    assert "1 denominators verified" in capsys.readouterr().out
