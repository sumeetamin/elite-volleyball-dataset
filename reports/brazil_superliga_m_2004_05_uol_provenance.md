# Brazil Superliga men 2004/05

The [UOL first-phase archive](https://web.archive.org/web/20070610060037/http://esporte.uol.com.br/volei/superliga/masc_jogos0405.jhtm) lists 110 dated results for 11 clubs. The source capture is retained at `sources/brazil_superliga_m_2004_05_uol_archive.tsv`; `scripts/import_brazil_m_2004_05_uol.py` normalizes the matches to `data/silver/brazil_superliga_m_2004_05_uol.csv`.

The importer requires all 55 unordered club pairings twice and reconciles set-score winners to the archived final standings for all 11 clubs. The regular-season result coverage is therefore 110/110 (100%). Five archived partial-score strings conflict with the listed match set score; the importer retains the listed match result, which agrees with final standings, and records each conflict in its output. This is a contemporary secondary source and has not been cross-checked against CBV match protocols. Playoffs are excluded.
