# Dataset acceptance target

Goal: cover selected competitions from 2000 through the latest completed season/date with **at least 80% of officially enumerated completed match results in each competition-season**. Keep regular-season and playoff coverage distinct. Selected scope: Italian SuperLega and Serie A1 Women, Polish PlusLiga and Tauron Liga, Brazilian Superliga men and women, CEV Champions League men and women, and World League/VNL plus World Grand Prix/VNL lineages.

Count only completed results in the numerator. Establish denominators from official fixtures/results or documented official format; partial page row counts are not denominators. Record source URL, stable source match ID, source hash, season, status and a reproducible match key. Separately audit score/result, box score, rally, rotation, lineup and odds completeness. Leave unknown coverage blank and document source gaps; do not claim a pooled percentage that hides season gaps.

## Evidence checkpoint (2026-11-06)

- Italian SuperLega men 2024/25 regular season: **132/132 (100%)**, deduplicated by Lega Volley `IdGara`; playoffs excluded.
- Brazilian Superliga men and women 2017/18–2024/25: **2,101/2,113 (99.43%)** completed regular-season results across 16 official season pages. Fifteen slices are at least 95%; men's 2019/20 is 126/132 (95.45%). Women's 2022/23 officially enumerates 133 fixtures and has 132 results (99.25%). Playoffs are kept separate. Source-page hashes and per-season figures are in `data/coverage/cbv_seasons.csv`.
- Across the currently denominator-verified slices (Italy SuperLega M 2024/25, PlusLiga M 2024/25, and Brazil M/F 2017/18–2024/25), every slice exceeds 80%. This is **not** the selected-scope 2000-to-date target: women's Italy, Poland, CEV and international histories remain incomplete or lack verified denominators.
- PlusLiga men 2024/25 has 240/240 outcomes but dates in only 176/240 rows (73.33%); its set-point cells are excluded because the PDF text layer contains contradictions.
- Brazilian Data Project imports preserve regular-season/playoff phase, retain scheduled rows without scores as unknown, and handle both observed team-name HTML encodings. The 2019/20 men's page has six unscored regular fixtures; they remain in its denominator. CEV and international archives are likewise incomplete for this target.

Refresh the generated audit from `config/competition_seasons.csv`; update this checkpoint only from that evidence. Target is complete only after all scoped seasons are met or have an explicitly verified disposition/source gap.
