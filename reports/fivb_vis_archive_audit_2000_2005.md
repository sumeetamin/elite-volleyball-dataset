# FIVB VIS historical archive probe: 2000–2005

Checked 2026-11-06 using the public FIVB VIS XML service. This is an availability audit, not a match-data backfill and not evidence that an edition did not take place.

## Reproducible official queries

The [VIS tournament-list request](https://www.fivb.org/VisSDK/VisWebService/GetVolleyTournamentList.html) accepts season and status filters. The request used `GetVolleyTournamentList`, fields `No Code Name Gender Season StartDate EndDate Status IsVisManaged OrganizerType OrganizerCode`, and filter `Seasons="2000 2001 2002 2003 2004 2005" Statuses="Scheduled Confirmed Running Finished Canceled" Genders="M W"`. FIVB returned HTTP 200, `NbItems=64`, list version 13289, response SHA-256 `a9659bc4e71f9662db6bb27f0d07f1513bd94332c454273587f7fa178a2524a1`.

The [VIS tournament record documentation](https://www.fivb.org/VisSDK/VisWebService/VolleyTournament.html) states that when `IsVisManaged` is false, a tournament is listed for the calendar only; associated teams, matches, results and other information cannot be requested. The [match-list request](https://www.fivb.org/VisSDK/VisWebService/GetVolleyMatchList.html) documents filtering by tournament number(s).

## Year-by-year disposition

| Edition year | Men's World League | Women's World Grand Prix | Evidence and what is unavailable |
| --- | --- | --- | --- |
| 2000 | Not listed in the matching VIS tournament index | Not listed in the matching VIS tournament index | No target event row/ID, teams, fixtures or match results returned by VIS. The query also returned VNL 2021 Finals entries with codes `MVNL2021F`/`WVNL2021F` but `Season=2000` and 2000 dates; these are a source date/season anomaly and were excluded. |
| 2001 | Not listed | Not listed | No matching tournament ID, fixture census or match results exposed by the VIS season index. |
| 2002 | Not listed | Not listed | No matching tournament ID, fixture census or match results exposed by the VIS season index. |
| 2003 | Not listed | Not listed | No matching tournament ID, fixture census or match results exposed by the VIS season index. |
| 2004 | Not listed | Not listed | No matching tournament ID, fixture census or match results exposed by the VIS season index. |
| 2005 | Listed, but not VIS-managed | Listed, but not VIS-managed | World League: No `105`, code `WL2005`, status Finished, `IsVisManaged=0`, no start/end date. Grand Prix: No `93`, code `WGP2005`, status Finished, `IsVisManaged=0`, dates 2005-06-24 to 2005-07-18. `GetVolleyMatchList` queried with both IDs returned `NbItems=0` (response SHA-256 `52108f40e2a0b4d23a479f95beac48ba1db9cacf372044d801c2c7b32766fa5d`). VIS therefore exposes event calendar metadata but no retrievable team/match/result rows for either 2005 event. |

Annual calendar-date queries for 2000–2005 in the existing VIS backfill returned zero rows (the empty responses share SHA-256 `48d5d5c74ea5ccdf9d798d15fd856e7a0df6f822313e48364ec59b1dc3b98828`). The season-index findings above explain the important distinction: zero annual-query rows are a source gap; the 2005 tournaments are explicitly listed but unmanaged, while the VNL 2021 Finals/2000 season collision shows the season index can contain misdated entries. These states are represented as `not_listed_in_official_vis_index` and `listed_but_unmanaged_in_vis`, not as zero-match seasons. No official match denominators are asserted for 2000–2005.

The current [FIVB competitions archive](https://www.fivb.com/volleyball/fivb-competitions/) visibly exposes World League and World Grand Prix event links for 2010–2017, and VNL links beginning in 2018. Its exposed historical page does not supply match-level 2000–2005 data. Page omissions and VIS availability must not be interpreted as proof that the historical competitions were not played; they remain source gaps for this dataset.
