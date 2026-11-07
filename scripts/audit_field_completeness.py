"""Build a per-source, per-season field availability audit from local match tables."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from volleyball_dataset.field_completeness import build_field_audit  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "field_completeness_2026-11-06.csv")
    args = parser.parse_args()
    paths = [p for p in args.data_dir.rglob("*.csv")
             if ("silver" in p.parts or "local" in p.parts)
             and "coverage" not in p.name.casefold()
             and "_sets" not in p.name.casefold()
             and "team_match_stats" not in p.name.casefold()]
    rows = build_field_audit(sorted(paths))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    measured = sum(row["availability"] == "measured" for row in rows)
    print(f"Wrote {len(rows)} source-season-field rows from {len(paths)} tables; {measured} groups measured.")


if __name__ == "__main__":
    main()
