# Italian Serie A1 women official results archive

`scripts/backfill_italy_women_official.py` discovers the official Serie A1 regular-season competition and every round link for each requested season. It caches raw HTML locally, parses official match-center IDs where available, retains source URLs and SHA-256 page hashes, and saves normalized rows to ignored `data/silver/italy_serie_a1_women_matches.csv`. The per-season census is in ignored `data/coverage_italy_women_historical.csv`. Playoffs and cups are excluded.

## Audited snapshot (2026-11-06)

- 26 completed seasons, 2000/01–2025/26: 3,701 eligible fixtures and 3,687 valid 3–0 through 3–2 results (99.62%). Every season exceeds the 80% result threshold.
- Only 3,124 completed results have an explicit match date. The 563 undated results are retained for score coverage and excluded from chronological model training. A round label is not treated as an exact match date.
- The 2019/20 archive enumerates 182 planned fixtures, of which 137 have results. The official [early-termination notice](https://www.legavolleyfemminile.it/igor-il-campionato-di-serie-a1-e-sospeso-definitivamente/) explains the abandoned remainder. The 45 unplayed fixtures are marked cancelled and excluded from the eligible-result denominator, while the 182 planned count remains visible in the local census.
- The 2026/27 season is in progress and was not included in this completed-season backfill.

The official season/round entry point is `https://www.legavolleyfemminile.it/risultati/?serie=1&stagione=YEAR`. Distinct match tables on all linked regular-season rounds establish each fixture census; the parser rejects malformed tables and dates outside the named July–June club season. `source_match_id` uses the match-center ID when provided and a deterministic match key otherwise. No source status is inferred from an absent date.

Rebuild the local data and main coverage snapshot:

```powershell
python scripts/backfill_italy_women_official.py --start-year 2000 --end-year 2025
volley-data coverage --inventory config/competition_seasons.csv --data-dir data --output reports/coverage_audit_2026-11-06.csv
```

Raw pages and match rows are local by default until league redistribution rights are confirmed. The generated main audit is aggregate metadata, not a substitute for the cached source-page and match-ID checks.
