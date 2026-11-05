# Historical match dataset: 2000–2026

This repository combines three sources with different scopes. It is a sourced compilation, not a complete census of world volleyball. Counts below describe records actually returned/imported; they do not imply that absent years had no matches.

## Included data

- `silver/fivb_vis_matches.csv`: 29,211 FIVB VIS match records dated 2000–2026, queried one calendar year at a time on 2026-11-05 UTC. This includes international matches and future/scheduled fixtures exposed by the public service; use `status` and set score fields to select completed outcomes. FIVB returned zero matches for 2000–2005. Per-year response counts, timestamps and hashes are in `coverage_fivb_vis.csv`.
- `silver/fivb_vis_sets.csv`: one row per FIVB set whose two point values are present. This is derived from the match file and carries the original source record identifiers and response hashes.
- `silver/volleyball_australia_matches.csv`: all **2,327** game rows counted by the archive across 26 seasons, with **2,218 rows from 2000–2025**; it also contains 1998–1999 records. The snapshot has 2,267 declared winners, one declared draw, and 59 games with unknown outcomes. Exact match dates are generally unavailable; `round_heading` preserves archive context. 2020 and 2021 have no listed games. The archive itself says some seasons are incomplete. See `coverage_volleyball_australia.csv`.
- `silver/mendeley_mens_worldcup_matches.csv`: 706 records from intermittent men's FIVB World Cup editions 1965–2019. From 2000 it contributes 330 records in 2003, 2007, 2011, 2015 and 2019. The source's numeric columns are ambiguous, so only the explicit winner is interpreted.

The counts overlap between sources. Do not sum them as unique global games; deduplication across differently scoped competitions and providers is not asserted. Team IDs are provider-specific and are not globally reconciled. FIVB set rows are available only where the service returned both teams' set points. Neither rally-level actions, player rotations, full box scores nor historical odds are supplied by this compilation.

## Source, rights and limits

FIVB VIS public API documentation: [service overview](https://www.fivb.org/VisSDK/VisWebService/Introduction.html), [request protocol](https://www.fivb.org/VisSDK/VisWebService/Requests.html), [match list](https://www.fivb.org/VisSDK/VisWebService/GetVolleyMatchList.html), and [match fields](https://www.fivb.org/VisSDK/VisWebService/VolleyMatch.html). Public access does not establish a blanket redistribution license; retain provenance and check applicable terms before republishing elsewhere.

Australian historical archive: [Volleyball Australia results archive](https://superleague.volleyball.org.au/info/history/results-archive-1998-2022/). It states that seasons are incomplete and team names are historical. The page does not declare an open-data license; the extracted source facts retain source text, URL and retrieval hash, but redistribution rights have not been confirmed. The repository is private; do not treat this as a license grant.

Mendeley attribution: Thaksheel Alleck, Tommaso Giovannelli, Luis Nunes Vicente, Roman Mitchell, and Ori Remen (2024), “Match Score Dataset for Team Ball Sports”, Version 2, DOI 10.17632/2pt4vmyf27.2, CC BY 4.0. [Dataset](https://data.mendeley.com/datasets/2pt4vmyf27/2).

## Rebuild / update

From the repository root, run `volley-data backfill-fivb --from-year 2000 --to-year 2026` to query FIVB and regenerate the set table; run `volley-data import-australia` to re-import the checked-in downloaded archive. FIVB historical query results can change; each raw response is archived locally by the adapter and hashed in the coverage file. Coverage starts at 2000 by design even when the source provides no records for a year.
