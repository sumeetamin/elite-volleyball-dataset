# FIVB Men's World League 2001

- Scope: all phases of the 2001 edition (16 teams), 112 completed matches.
- Result source: [OSSCG federation archive (Wayback)](https://web.archive.org/web/20080516194949/http://www.osscg.org.yu/volleyball_WL2005/2_historyWL_2001.asp).
- Date and match-table index: [2001 World League match tables](https://newikis.com/en/2001_FIVB_Volleyball_World_League), a CC BY-SA 4.0 mirror of the Wikipedia article.
- The retained TSV sources/fivb_world_league_2001_match_table.tsv contains one row per match-table entry. Stable source record IDs preserve table order.
- Denominator: four preliminary pools × 24 matches = 96; two final pools × 6 = 12; semifinals = 2; bronze match and final = 2; total = 112. The importer enforces the 96/12/2/1/1 phase census.
- Cross-check: all 112 team pairings and set results were reconciled against the archived federation listing. Computed wins reconcile to all four preliminary and both final-pool standings. The final also agrees with the published medal results (Brazil gold, Russia bronze).
- Set-point data is excluded from silver. An archived set-point string disagreed with the match-table capture; result-level outcomes agreed. The retained source table intentionally includes only dates, teams, phase, and set result.
- The importer validates the season year, unique IDs, match-result bounds, phase census, and six pool standings before producing data/silver/fivb_legacy_world_league_2001_matches.csv.
- Source payload SHA-256 is written into each silver row by scripts/backfill_fivb_world_league_2001.py.
- Redistribution terms for the OSSCG archive are unverified. The indexed page is CC BY-SA 4.0; review reuse obligations before public redistribution.
