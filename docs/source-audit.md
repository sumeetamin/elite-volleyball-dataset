# Source audit and field coverage

Before enabling a provider, record competition, season, sample date range, expected and observed match counts, fields present, corrections behavior, access terms, retrieval time, and audit reviewer in `manifests/source_registry.csv`. Sample at least 30 matches across seasons and include playoffs, five-set matches, postponements, and missing-stat cases. Do not assume a provider's league listing guarantees historical box-score or odds coverage.

Suggested authoritative tiers:

1. FIVB VIS documented service for international event schedules/results and public match documents.
2. Official league websites and authorized league feeds for club records.
3. API-Volleyball as a convenience source only after endpoint-by-endpoint audit.
4. Authorized DataVolley files for rally/touch/rotation detail. OpenVolley parser documentation describes the file semantics; it is not a source of match files.
5. Odds provider selected only after verifying sport, market, bookmaker, timestamp frequency, historical depth, and permitted retention. Do not assume The Odds API has volleyball coverage.

Source conflicts are retained and reconciled field-by-field; provenance is never discarded.
