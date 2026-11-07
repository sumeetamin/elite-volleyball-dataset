# Brazil Superliga men 2006/07: first-phase results

The [archived UOL results page](https://web.archive.org/web/20080709003311/http://esporte.uol.com.br/volei/superliga/masc_jogos0607.jhtm) captures the complete regular-season first phase. Its final standings list 15 clubs with 28 matches apiece, establishing 210 expected matches (15 × 28 ÷ 2). The archived result rows contain all 210 fixtures: 15 rounds of seven matches in each turn, 105 unordered pairings played twice, with each directed home/away fixture present once. All 15 clubs have 28 appearances.

The normalized results are in `data/silver/brazil_superliga_m_2006_07_uol.csv`; the text capture is in `sources/brazil_superliga_m_2006_07_uol_archive.tsv`. `scripts/import_brazil_m_2006_07_uol.py` performs the fixture, round, team-appearance and standings-win checks. It produces **210/210 (100%)** first-phase result coverage. Playoffs are excluded.

Two UOL score captions conflict with both their printed partial set scores and the final standings. At source row 183, Náutico–Betim is shown as 3–2, while the five set scores and final table support 2–3. At row 184, Santo André–Bento is shown as 0–3, while its three printed set scores and final table support 3–0. The importer keeps the original caption values in the source TSV and corrects the normalized match outcomes using the two independent checks. With these corrections, every team's match-win total matches the final standings exactly.

Eight additional partial-score strings conflict with the match outcomes. Since the outcome corrections above reconcile the full season to the standings, the normalized table contains match outcomes only; it omits set-point details. Every discrepancy is listed in `reports/brazil_superliga_m_2006_07_uol_conflicts.csv`.

The [UOL regulation page](https://www.uol.com.br/esporte/volei/superliga/masc_reg0607.jhtm) documents the 15-team competition format. This is a contemporary secondary archive and has not been reconciled to official CBV match protocols. The SHA-256 stored in each normalized row covers the retained local TSV capture, not the upstream HTML bytes. Match IDs are deterministic derived keys, not IDs assigned by UOL.
