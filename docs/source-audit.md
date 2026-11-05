# Source audit and field coverage

Before enabling a provider, record competition, season, sample date range, expected and observed match counts, fields present, corrections behavior, access terms, retrieval time, and audit reviewer in `manifests/source_registry.csv`. Sample at least 30 matches across seasons and include playoffs, five-set matches, postponements, and missing-stat cases. Do not assume a provider's league listing guarantees historical box-score or odds coverage.

Suggested authoritative tiers:

1. FIVB VIS documented service for international event schedules/results and public match documents.
2. Official league websites and authorized league feeds for club records.
3. API-Volleyball as a convenience source only after endpoint-by-endpoint audit.
4. Authorized DataVolley files for rally/touch/rotation detail. OpenVolley parser documentation describes the file semantics; it is not a source of match files.
5. Odds provider selected only after verifying sport, market, bookmaker, timestamp frequency, historical depth, and permitted retention. Do not assume The Odds API has volleyball coverage.

Source conflicts are retained and reconciled field-by-field; provenance is never discarded.

## Backfill from 2000

API-Volleyball supports league/season game queries, but historical depth varies by competition and subscription. The backfill CLI archives each raw season response and writes a per-league/year report through the current UTC year. Obtain IDs from the provider's league endpoint, audit early, middle, and recent seasons, and confirm account entitlement before a full run. A zero-row response is recorded as zero; it does not prove that the season had no matches. The report is raw response coverage, not a complete canonical dataset.

FIVB VIS documents public volleyball match-list requests with date filters and versioning. Public access does not guarantee full coverage back to 2000 or all leagues. Compare each year with official calendars, and account for fields that are not public.

The published open volleyball match-score dataset described in the 2024 Data in Brief article contains 706 matches from selected men's FIVB World Cup editions only (1965–2019, intermittent); it cannot satisfy a 2000-to-current all-league requirement. The CC BY 4.0 file is included as a clearly scoped starter subset under data/. Its source CSV headers are inconsistent, so only the explicit winner field is treated as a usable outcome; other numeric fields remain unverified raw values.
