# Historical match dataset: 2000–2026

This repository combines three sources with different scopes. It is a sourced compilation, not a complete census of world volleyball. Counts below describe records actually returned/imported; they do not imply that absent years had no matches.

## Included data

- `silver/fivb_vis_matches.csv`: 29,211 FIVB VIS match records dated 2000–2026, queried one calendar year at a time on 2026-11-05 UTC. This includes international matches and future/scheduled fixtures exposed by the public service; use `status` and set score fields to select completed outcomes. FIVB returned zero matches for 2000–2005. Per-year response counts, timestamps and hashes are in `coverage_fivb_vis.csv`.
- `silver/fivb_vis_sets.csv`: one row per FIVB set whose two point values are present. This is derived from the match file and carries the original source record identifiers and response hashes.
- `silver/volleyball_australia_matches.csv`: all **2,327** game rows counted by the archive across 26 seasons, with **2,218 rows from 2000–2025**; it also contains 1998–1999 records. The snapshot has 2,267 declared winners, one declared draw, and 59 games with unknown outcomes. Exact match dates are generally unavailable; `round_heading` preserves archive context. 2020 and 2021 have no listed games. The archive itself says some seasons are incomplete. See `coverage_volleyball_australia.csv`.
- `silver/mendeley_mens_worldcup_matches.csv`: 706 records from intermittent men's FIVB World Cup editions 1965–2019. From 2000 it contributes 330 records in 2003, 2007, 2011, 2015 and 2019. The source's numeric columns are ambiguous, so only the explicit winner is interpreted.
- `silver/ncaa_matches.csv`: 108,245 NCAA match summaries covering women’s D-I matches from 2018–2025, plus women’s D-II/D-III and men’s D-I/D-III from 2020–2024. These include 2020–2024 matches (and scheduled/cancelled rows where the source lists them); source-row perspectives are grouped by season, date and team pair. `coverage_ncaa.csv` lists the exact available slices.
- `silver/ncaa_team_match_stats.csv`: 183,221 team-perspective rows with team box-score statistics (kills, errors, attacks, assists, digs, blocks, etc.) for the same NCAA coverage. These are a different data grain from the match summary and must not be added to match totals. 2018–2019 are one record per listed match in the upstream women's D-I archive; 2020–2024 team-perspective files can contain both sides of the same match. The upstream 2025 women's D-I file is explicitly reported as incomplete; don't treat its 5,068 grouped rows as a season census.

The counts overlap between sources. Do not sum them as unique global games; deduplication across differently scoped competitions and providers is not asserted. Team IDs are provider-specific and are not globally reconciled. FIVB set rows are available only where the service returned both teams' set points. NCAA rows add team box-score aggregates but not the rally feed, rotations or player-level history. Historical bookmaker odds are not supplied by this compilation.

## Source, rights and limits

FIVB VIS public API documentation: [service overview](https://www.fivb.org/VisSDK/VisWebService/Introduction.html), [request protocol](https://www.fivb.org/VisSDK/VisWebService/Requests.html), [match list](https://www.fivb.org/VisSDK/VisWebService/GetVolleyMatchList.html), and [match fields](https://www.fivb.org/VisSDK/VisWebService/VolleyMatch.html). Public access does not establish a blanket redistribution license; retain provenance and check applicable terms before republishing elsewhere.

Australian historical archive: [Volleyball Australia results archive](https://superleague.volleyball.org.au/info/history/results-archive-1998-2022/). It states that seasons are incomplete and team names are historical. The page does not declare an open-data license; the extracted source facts retain source text, URL and retrieval hash, but redistribution rights have not been confirmed. The repository is private; do not treat this as a license grant.

Mendeley attribution: Thaksheel Alleck, Tommaso Giovannelli, Luis Nunes Vicente, Roman Mitchell, and Ori Remen (2024), “Match Score Dataset for Team Ball Sports”, Version 2, DOI 10.17632/2pt4vmyf27.2, CC BY 4.0. [Dataset](https://data.mendeley.com/datasets/2pt4vmyf27/2).

NCAA data references: [ncaavolleyballr's archived CSV files](https://jeffreyrstevens.github.io/ncaavolleyballr/articles/data.html) and [download archive](https://github.com/JeffreyRStevens/ncaavolleyballr/tree/main/data-csv); [2018–2021 women’s archive and MIT-licensed scraper](https://github.com/mattwaite/NCAAWomensVolleyballData). The underlying records are NCAA statistics submitted by participating institutions; the upstream scraper/data repositories do not establish NCAA's blanket redistribution terms. The 2025 CSV has a maintainer issue noting partial coverage: [upstream report](https://github.com/JeffreyRStevens/ncaavolleyballr/issues/24).

## Rebuild / update

From the repository root, run `volley-data backfill-fivb --from-year 2000 --to-year 2026` to query FIVB and regenerate the set table; run `volley-data import-australia` to re-import the downloaded archive; run `volley-data import-ncaa` to rebuild the NCAA CSVs from `data/bronze/ncaa`. FIVB historical query results can change; each raw response is archived locally by the adapter and hashed in the coverage file. Coverage starts at 2000 by design even when the source provides no records for a year.
