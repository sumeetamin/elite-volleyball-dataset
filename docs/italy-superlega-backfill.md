# Italian SuperLega historical result backfill

The reusable downloader/parser is `scripts/backfill_italy_superlega_official.py`. It discovers each season's regular-season competition ID from the official Lega Volley calendar page, downloads first and return legs, imports completed scores by official `IdGara`, retains source URLs and SHA-256 values, and counts official participant IDs from the same schedule pages.

## Coverage snapshot (2026-11-06)

- Seasons 2000/01–2025/26: **4,257 completed results out of 4,282 expected double-round-robin fixtures** (99.42% pooled over the completed seasons). Each of the 26 season slices meets 80%.
- 2019/20 was officially ended early: 13 teams imply 156 home-and-away fixtures; the archive contains 131 completed outcomes (83.97%). The archived league decision is reflected in the season status instead of treating the unfinished schedule as a normal complete season.
- The current 2026/27 season is **in progress**: 24 results captured out of 132 expected regular-season fixtures (18.18% as of the capture date). It is reported separately and is not treated as a completed-season coverage failure.
- Total observed output including current season: **4,281 matches across 27 season labels**.

The denominator is the number of teams in the official regular-season pages multiplied by `teams - 1`, for the documented home-and-away round-robin format. The number of distinct official match IDs is cross-checked and separately reported. This handles early season termination in 2019/20 and avoids treating only already-played games in 2026/27 as the full season schedule.

Coverage details, season-specific competition IDs, exact source URLs, raw-source hashes, captured `IdGara` counts and retrieval times are in [`reports/italy_superlega_historical_coverage_2026-11-06.csv`](../reports/italy_superlega_historical_coverage_2026-11-06.csv). The normalized match output is generated locally at `data/silver/italy_superlega_matches_2000_2026.csv` (4,281 data rows; SHA-256 `df10001043cb587b0e6cd9cff4ffdc5e5faa3192bf2345bf37e96fac22195a0f`). Raw HTML is retained locally under `data/bronze/` and is not committed by this repository's default data policy.

## Rebuild

```powershell
python scripts/backfill_italy_superlega_official.py --start-year 2000 --end-year 2026
```

Raw page names follow `italy_superlega_YYYY_YY_{first,return}_leg.html`. Existing raw captures are reused; remove a specific capture to refresh it. The current season is captured as available on the day of retrieval, so repeat the command to update its results.

Official source pattern: [Lega Volley calendar](https://ww2.legavolley.it/Calendario.asp?Anno=2024&IdCampionato=947), with separate `IdFase=1` (first leg) and `IdFase=2` (return leg). For the 2019/20 early closure see the [official season completion table](https://www.legavolley.it/wp-content/uploads/2020/08/SuperLegaTerminatoRS.pdf).
