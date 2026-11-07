# Brazil Superliga men 1999/2000

Source: [contemporary UOL first-phase archive](https://web.archive.org/web/20070610061220/http://esporte.uol.com.br/volei/superligamasc9900fase1.htm), captured in `sources/brazil_superliga_m_1999_2000_uol_archive.tsv` through the in-app browser. The source lists 170 dated scores. Its final standings have 13 clubs with 24 matches each and explicitly state that Maringá withdrew. Fourteen listed rows involving Maringá are retained in the source capture but excluded from the normalized season because they are absent from the final standings.

`scripts/import_brazil_m_1999_2000_uol.py` normalizes the other 156 rows. Validation requires all 78 active-club pairs to appear twice and every club's wins to match the archived final table. Match IDs are deterministic derived hashes, not official IDs. The normalized scores and dates are complete for the regular season; official CBV match-sheet and playoff reconciliation remains pending.
