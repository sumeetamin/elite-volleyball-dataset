# Brazil Superliga women 2008/09 result capture

## Sources

- UOL first tournament: <https://www.uol.com.br/esporte/volei/2008/superliga/jogos01_fem.jhtm>
- UOL second tournament: <https://www.uol.com.br/esporte/volei/2008/superliga/jogos02_fem.jhtm>
- UOL third tournament: <https://www.uol.com.br/esporte/volei/2008/superliga/jogos03_fem.jhtm>
- UOL fourth tournament: <https://www.uol.com.br/esporte/volei/2008/superliga/jogos04_fem.jhtm>
- UOL playoffs: <https://www.uol.com.br/esporte/volei/2008/superliga/finais_fem.jhtm>
- UOL competition regulations: <https://www.uol.com.br/esporte/volei/2008/superliga/regulamento_fem.jhtm>
- CBV historical editions index: <https://wp.cbv.com.br/superliga/outras-edicoes>
- Contemporaneous report that CBV published the official tables and describing the four-turn format: <https://www.correiobraziliense.com.br/app/noticia/superesportes/2008/10/16/interna_superesportes%2C41186/superliga-ja-tem-data-hora-e-lugar-para-comecar.shtml>
- Contemporary report on CBV's four-turn format and playoff structure: <https://www.correiobraziliense.com.br/app/noticia/superesportes/2008/10/15/interna_superesportes%2C40947/amp.shtml>

## Reproducible capture

- Input: `sources/brazil_superliga_w_2008_09_uol_archive.tsv`
- Importer: `scripts/import_brazil_w_2008_09_uol.py`
- Normalized output: `data/silver/brazil_superliga_w_2008_09_uol.csv` (generated and ignored)
- SHA-256 of retained TSV: `6bee8daa45169628eb066afe2e5c0c2cd114189850e44f78f4b00b74b6a3b8dc`
- The hash is for the local transcription, not the upstream HTML bytes. The capture retains derived stable match IDs and source page URLs.

## Reconciliation

The source capture contains 152 dated completed results: 31 first-tournament matches (30 pool, one final), 37 second-tournament matches (36 pool, one final), 37 third-tournament matches (36 pool, one final), 31 fourth-tournament matches (30 pool, one final), and 16 playoff matches (eight quarterfinal, six semifinal, bronze, championship). The expected census is therefore 30 + 36 + 36 + 30 pool fixtures, four tournament finals, and 16 playoff fixtures = **152**. A contemporary report records that CBV published the official season tables and describes its four-turn competition structure; the UOL schedule/results archive enumerates the corresponding matches. UOL's regulation page and the reporter's account differ in the ordinal assignment of intra-group vs cross-group tournament legs, so the denominator is based on the independently counted complete stage tables and reconciled standings, not on assuming that ordinal wording. The importer rejects an incorrect phase/round census, duplicate match key, unrecognized club, invalid best-of-five score, or any discrepancy between pool match wins and the UOL standings totals for each tournament.

The table's native club labels are retained, including Rexona, Finasa, Brasil Telecom, and Banespa; legacy imports with modernized or conflicting aliases are superseded. Tournament group standings reconcile against pool wins. Tournament finals are excluded from those pool standings checks.

## Coverage limitation

The inventory records **152/152 listed outcomes** against this stage census. This is an auditable complete-schedule census supported by contemporaneous reporting of official CBV tables and the complete UOL archive; it is not a direct retained CBV PDF snapshot. Official CBV match-sheet reconciliation and set-point verification remain desirable and are not implied by the 100% match-result count. The reported percentage covers match outcomes only, not box scores or rally/rotation/lineup/odds fields.
