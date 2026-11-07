# FIVB World League 2000 coverage and provenance

## Verified coverage

- Men's FIVB World League 2000: **89/89 match results (100%)**, all dated.
- Denominator: 72 intercontinental matches (three pools of four teams, double round-robin: 3 × 4 × 3), plus 15 final-round pool matches (six teams, five rounds), plus bronze and gold medal matches = 89.
- The 12-team initial pool standings and six-team final-round win totals reconcile to the archived results.
- Every indexed result was compared to its corresponding archived OSSCG match. The two final-round games with Yugoslavia have the opposite display order in the archive and date table; winner and match result agree after team-order normalization.
- 86/89 set-point strings agree after normalizing team order. Three point-score discrepancies are retained in the source capture and omitted from normalized silver; only result-level data are claimed.
- Team aliases are normalized: Yugoslavia/FR Yugoslavia → FR Yugoslavia; Brasil → Brazil; USA → United States.
- Silver IDs are deterministic local IDs incorporating the archive page line and occurrence; they are not official FIVB match IDs.

## Sources

- Archived federation historical results and standings: [OSSCG World League 2000 archive](https://web.archive.org/web/20080516194944/http://www.osscg.org.yu/volleyball_WL2005/2_historyWL_2000.asp).
- Match dates and table row references: [2000 FIVB World League match tables](https://en.wikipedia.org/wiki/2000_FIVB_Volleyball_World_League).
- Champion, runner-up and bronze medal cross-check: [FIPAV World League historical winners](https://www.federvolley.it/world-league).

## Reproducibility

Run `python scripts/backfill_fivb_world_league_2000.py`. The importer checks all 89 outcomes against the archived result captured in the source TSV, validates 72/15/2 phase counts and standings, and writes `data/silver/fivb_legacy_world_league_2000_matches.csv`. The TSV's SHA-256 is included in silver; it covers the retained structured extraction, not the original archived webpage bytes. The archived text excerpt is retained at `sources/fivb_world_league_2000_osscg_text_capture.txt`.

