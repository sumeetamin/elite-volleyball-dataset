# PlusLiga men 2008/09 source reconciliation gap

The official final standings page verifies 10 teams with 18 regular-season matches each, so the denominator is **90**. Its SHA-256 is `5ab8030fb4fea7e98965afe2dcde2f8dd1f7b881a4ec465c3ba0b8adbd9022dc`.

The official team-pair archive has 45 pages and 90 regular-season rows (plus 36 playoff and 4 playout rows). The team-season pages provide 180 dated team-side records, but their chart IDs are not the game IDs in the pair pages. Matching by opponent and set score uniquely resolves 128 team-side records; 52 remain ambiguous because the same opponent/result combination occurs more than once.

The official match-detail route did not resolve the conflict: of 130 downloaded detail pages, only 28 passed strict matchup-and-score validation against the pair archive. For example, pair archive game ID `1392` records Asseco Resovia–Delecta Bydgoszcz as 3–2, while its detail page displays 3–1. The official Resovia team archive lists the 3–2 result on 3 January 2009: [team archive](https://www.tauronliga.pl/teams/tour/9/id/3.html). This is source disagreement, not a basis for choosing or inferring a result.

No 2008/09 rows are admitted to the normalized match table or coverage numerator until every fixture can be reconciled. The denominator is retained as verified; result coverage stays blank. Exact page URLs and SHA-256 hashes for the 186 captured pages are in [`plusliga_m_2008_09_source_inventory.csv`](plusliga_m_2008_09_source_inventory.csv). Local HTML captures remain in ignored `data/bronze/plusliga_m_2008_09/`.
