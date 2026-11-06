# Tauron Liga archive audit: 2015/16

Audit date: 2026-11-06

## What the official archive exposes

The official Tauron Liga site has indexed per-match pages for the 2015/16 women's top division (played under the ORLEN Liga name). A page indexed as `Mecze - Sezon 2015/2016` reports a regular-phase match dated 28 October 2015, match number 7, and a 0–3 result with set scores 13–25, 20–25, 23–25. The search index also exposes match-level stats pages for 2015/16. This is evidence that match outcomes exist in the league's official archive; it is not a complete season result ledger.

- Match detail example: <https://www.tauronliga.pl/games/action/show/id/5474/tour/24.html>
- Alternate indexed match detail: <https://www.tauronliga.pl/games/action/show/id/5493/tour/24/nocookies/1.html>
- Official 2015/16 season table: <https://www.tauronliga.pl/table/tour/23/nocookies/www.bilety.energaindykpolazs.pl>
- Official season/team stats archive example: <https://www.tauronliga.pl/statsTeams/teams_1/64/tournament_1/23/id/75/type/teams.html>

The search index displays the example match's date, match number, set-level points, and final set result. The first match detail URL returned HTTP 404 through the web reader during this audit, while direct local retrieval failed DNS resolution. Thus the page payload could not be saved, hashed, or independently replayed. The indexed extraction is useful discovery evidence, but cannot substitute for an archived official HTML response.

## Denominator and coverage status

No authoritative season schedule listing the complete set of 2015/16 regular-phase fixture IDs was retrievable in this audit. The season table confirms the archived season and phase structure, but its extracted text only displays final standings and playoff format. Match #7 alone does not establish the fixture denominator. Consequently, no numerator or coverage percentage is recorded, and no match rows are imported.

## Reproducibility and next step

Before implementing an importer, retrieve the official season match-list page plus each match detail page in an environment with access to `tauronliga.pl`; save response bytes locally, record SHA-256 and retrieval timestamps, and establish the complete regular-phase denominator from the official schedule/round list. Then reconcile each match number, date, teams, set count, and set points against the same official archive. Confirm terms for redistribution before publishing raw pages or result rows; this audit found no explicit open-data license.

Source URLs above are the official league domain. Search-engine indexed content can change and is not itself a stable downloadable source. No repository data/config/coverage files were changed for this league.
