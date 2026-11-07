"""Import 2025/26 CBV official-site score tables from cached HTML pages."""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from volleyball_dataset.import_cbv_official_site import (  # noqa: E402
    MATCH_FIELDS, PAGES, REGULAR_FIXTURES, SEASON, parse_page,
)

RAW_DIR = ROOT / "data" / "bronze"
SILVER = ROOT / "data" / "silver" / "cbv_superliga_matches.csv"
COVERAGE = ROOT / "reports" / "cbv_2025_26_coverage.csv"
INVENTORY = ROOT / "reports" / "cbv_2025_26_source_inventory.csv"
SEASON_LEDGER = ROOT / "data" / "coverage" / "cbv_seasons.csv"


def _read_page(sex: str, refresh: bool = False) -> bytes:
    path = RAW_DIR / f"cbv_2025_26_{'men' if sex == 'M' else 'women'}.html"
    if path.exists() and not refresh:
        return path.read_bytes()
    request = Request(PAGES[sex], headers={"User-Agent": "EliteVolleyballDataset/0.1 (historical research)"})
    with urlopen(request, timeout=45) as response:
        payload = response.read()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    time.sleep(0.25)
    return payload


def _write(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def import_season(refresh: bool = False) -> dict[str, int]:
    matches: list[dict[str, object]] = []
    coverage: list[dict[str, object]] = []
    source_inventory: list[dict[str, object]] = []
    season_ledger: list[dict[str, object]] = []
    for sex in ("M", "F"):
        source_url = PAGES[sex]
        payload = _read_page(sex, refresh)
        rows, digest = parse_page(payload, sex, source_url)
        regular = [r for r in rows if r["phase"] == "regular_season"]
        complete = [r for r in regular if r["match_status"] == "completed"]
        matches.extend(rows)
        coverage.append({
            "competition_key": "brazil_superliga", "competition": "Brazil Superliga",
            "sex": sex, "season": SEASON, "phase": "regular_season",
            "expected_matches": REGULAR_FIXTURES, "observed_fixtures": len(regular),
            "completed_results": len(complete), "dated_fixtures": sum(bool(r["match_date"]) for r in regular),
            "coverage_pct": round(100 * len(complete) / REGULAR_FIXTURES, 4),
            "target_pct": 80, "target_met": "yes" if len(complete) / REGULAR_FIXTURES >= .8 else "no",
            "denominator_method": "official CBV page match IDs 1-132; 12 teams x 22 GP / 2",
            "source_url": source_url, "source_sha256": digest,
        })
        coverage.append({
            "competition_key": "brazil_superliga", "competition": "Brazil Superliga",
            "sex": sex, "season": SEASON, "phase": "playoffs",
            "expected_matches": "", "observed_fixtures": sum(r["phase"] == "playoffs" for r in rows),
            "completed_results": sum(r["phase"] == "playoffs" and r["match_status"] == "completed" for r in rows),
            "dated_fixtures": sum(r["phase"] == "playoffs" and bool(r["match_date"]) for r in rows),
            "coverage_pct": "", "target_pct": 80, "target_met": "unknown",
            "denominator_method": "Playoff outcomes retained separately; official playoff denominator not asserted.",
            "source_url": source_url, "source_sha256": digest,
        })
        source_inventory.append({
            "page_type": "official_cbv_match_table", "sex": sex, "season": SEASON,
            "source_url": source_url, "source_sha256": digest, "bytes": len(payload),
            "parsed_match_rows": len(rows), "parsed_regular_fixtures": len(regular),
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        })
        season_ledger.append({
            "source": "CBV official website",
            "competition": "Superliga Masculina" if sex == "M" else "Superliga Feminina",
            "sex": sex, "season": SEASON, "competition_id": "",
            "match_records": len(rows), "parsed_regular_rows": len(regular),
            "expected_regular_matches": REGULAR_FIXTURES,
            "completed_regular_matches": len(complete),
            "regular_coverage_pct": round(100 * len(complete) / REGULAR_FIXTURES, 4),
            "status": "retrieved", "source_url": source_url,
            "raw_file": f"data/bronze/cbv_2025_26_{'men' if sex == 'M' else 'women'}.html",
            "source_sha256": digest,
        })

    # Merge idempotently into the local, ignored outcome table. The official
    # pages remain local until their redistribution terms are reviewed.
    existing: list[dict[str, str]] = []
    old_fields: list[str] = []
    if SILVER.exists():
        with SILVER.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            old_fields = reader.fieldnames or []
            existing = [row for row in reader if not (row.get("season") == SEASON and row.get("source") == "CBV official Superliga website")]
    fields = list(dict.fromkeys(old_fields + MATCH_FIELDS))
    _write(SILVER, existing + matches, fields)
    _write(COVERAGE, coverage, list(coverage[0]))
    _write(INVENTORY, source_inventory, list(source_inventory[0]))
    old_ledger: list[dict[str, str]] = []
    ledger_fields = list(season_ledger[0])
    if SEASON_LEDGER.exists():
        with SEASON_LEDGER.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            ledger_fields = list(reader.fieldnames or ledger_fields)
            old_ledger = [row for row in reader if not (
                row.get("season") == SEASON and row.get("source") == "CBV official website")]
    _write(SEASON_LEDGER, old_ledger + season_ledger, ledger_fields)
    counts = {sex: int(row["completed_results"]) for sex, row in zip(("M", "F"), coverage[::2])}
    print(f"{SEASON}: men {counts['M']}/{REGULAR_FIXTURES}; women {counts['F']}/{REGULAR_FIXTURES} completed regular-season results")
    return counts


if __name__ == "__main__":
    import_season()
