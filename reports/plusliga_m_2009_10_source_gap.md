# PlusLiga men 2009/10 source reconciliation gap

Official standings verify 10 teams with 18 regular-season matches each, for a **90-match denominator**. The standings page SHA-256 is `41b668ec7f9e34fcb1c42349fa4345121f1dbedfef47c4109b0978db6e042383`.

The 45 official team-pair pages contain 90 regular-season result rows, 39 playoff rows, and 6 playout rows. However, team-season chart IDs do not match the pair-page game IDs. The official detail route also conflicts with the pair archive: game ID `1661` is 0–3 for Jadar Radom vs Asseco Resovia in the pair archive, while its detail page displays 3–1. The strict backfill therefore stops and imports no results or dates.

The denominator is retained as verified, but result coverage remains blank until the official records reconcile. URLs and hashes for the 191 captured pages are in [`plusliga_m_2009_10_source_inventory.csv`](plusliga_m_2009_10_source_inventory.csv); local HTML captures remain in ignored `data/bronze/plusliga_m_2009_10/`.
