# PlusLiga 2000/01 official archive recovery

The official site does not expose one season-wide historical results list for this period. The reusable importer discovers the official participants from the season's final regular-season table, then queries the all-time head-to-head page for each unique team pairing:

```powershell
python scripts/backfill_plusliga_2000_01_h2h.py
```

## Evidence snapshot (2026-11-06)

- The official 2000/01 table lists **10 teams**, each with **18 regular-season matches**, establishing a 90-match denominator (`10 × 18 / 2`).
- All 45 distinct team-pair archive pages were parsed. They yield **90/90 (100%) regular-season outcomes**, exactly two home/away results per pair.
- The archive also exposes **44 playoff** and **6 play-out** outcomes. Their denominators have not yet been independently verified, so they are retained as separate phases without coverage percentages.
- The normalized local file contains 140 unique official game IDs, SHA-256 `3f0eb508d1f3b63e26ad270ac9c4dd233695a9f7514344a1d8e4c7eeefccc1f0`. **All 140 match dates are blank** in the comparison archive output, so this slice is not ready for chronological model training until dates are reconciled from a dated official schedule or other verified source.

Coverage metadata and source hashes are in [`reports/plusliga_m_2000_01_h2h_coverage_2026-11-06.csv`](../reports/plusliga_m_2000_01_h2h_coverage_2026-11-06.csv); the 45 individual pair-source URLs/hashes are in [`reports/plusliga_m_2000_01_h2h_source_inventory_2026-11-06.csv`](../reports/plusliga_m_2000_01_h2h_source_inventory_2026-11-06.csv). The normalized results remain local at `data/silver/plusliga_m_2000_01_head_to_head.csv` while redistribution rights are reviewed. Raw HTML remains ignored locally.

The official archive warns that 2000/01–2007/08 historical figures still need final verification against paper match protocols. The 100% here means all denominator slots are represented in the current official head-to-head result archive; it does not remove that source caveat.

Sources: [official 2000/01 final table](https://www.plusliga.pl/table/tour/1/nocookies/1.html), [official example team comparison](https://www.plusliga.pl/statsTeams/teams_1/24/teams_2/68/type/teamsComparator.html), and the [league's 25-year history](https://www.plusliga.pl/news%2C25-lat-polskiej-ligi-siatkowki.html).
