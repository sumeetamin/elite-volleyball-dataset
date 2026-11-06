# Source audit and field coverage

Before enabling a provider, record competition, season, sample date range, expected and observed match counts, fields present, corrections behavior, access terms, retrieval time, and audit reviewer in `manifests/source_registry.csv`. Sample at least 30 matches across seasons and include playoffs, five-set matches, postponements, and missing-stat cases. Do not assume a provider's league listing guarantees historical box-score or odds coverage.

Suggested authoritative tiers:

1. FIVB VIS documented service for international event schedules/results and public match documents.
2. Official league websites and authorized league feeds for club records.
3. API-Volleyball as a convenience source only after endpoint-by-endpoint audit.
4. Authorized DataVolley files for rally/touch/rotation detail. OpenVolley parser documentation describes the file semantics; it is not a source of match files.
5. Odds provider selected only after verifying sport, market, bookmaker, timestamp frequency, historical depth, and permitted retention. Do not assume The Odds API has volleyball coverage.

Source conflicts are retained and reconciled field-by-field; provenance is never discarded.

## Selected club-league archive audit (November 2026)

- Brazil CBV Data Project lists Superliga men/women seasons from 2017/18 through 2024/25. The corrected parser uses each match row's own parent phase and round IDs; the previous parser incorrectly read the first round ID repeated elsewhere in each row. Across 16 official archived pages, 2,113 regular-phase fixture IDs are enumerated and 2,101 have final results (99.43%). The 2022/23 women's schedule lists 133 IDs; retain the source count as an anomaly. The 2019/20 men's page includes six scheduled but unscored games during the pandemic interruption. Source hashes and per-season rates are recorded in `data/coverage/cbv_seasons.csv`. Sources: [CBV history index](https://cbv-web.dataproject.com/MainHome.aspx), [CBV 2024/25 regulations](https://wp.cbv.com.br/wp-content/uploads/2024/10/199.2-REC-REGULAMENTO-ESPECIFICO-DA-COMPETICAO-SUPERLIGA-TEMPORADA-2024.2025.pdf).
- Italy men's 2024/25 official round calendar is available at [Lega Volley](https://ww2.legavolley.it/Calendario.asp?Anno=2024&IdCampionato=947). The downloaded page includes match scores and postponed fixtures, so completed and not-yet-played rows need separate status handling.
- Italy women's 2024/25 official schedule PDF is available at [Lega Volley Femminile](https://www.legavolleyfemminile.it/wp-content/uploads/2024/07/Calendario_Serie-A1_-24-25_Esteso-3.pdf). Its official club result pages expose season and round filters; result extraction remains pending.
- PlusLiga reports that it opened digital historical statistics from 2000/01; the league notes early seasons 2000/01–2007/08 have less detailed aggregate data. The official 2024/25 regular-season PDF enumerates match IDs 001–240 with dates, teams and match results. The normalized slice contains all 240 IDs (100% of the official enumerated regular-season total); dates are available for 176/240 rows (73.33%). Set-point columns were excluded because the PDF text layer contains malformed/contradictory set values. Playoffs are outside this denominator. Sources: [official 2024/25 match PDF](https://www.plusliga.pl/dl/625351/fd7c66/Faza_Zasadnicza_PL_2024-2025.pdf), [league archive announcement](https://www.tauronliga.pl/news%2Cplusliga-uruchomila-cyfrowe-statystyki-od-pierwszego-zawodowego-sezonu.html).

The Italian men’s 2024/25 official calendar provides both 11-round legs. The regular-season denominator is 132 matches (12 teams, double round robin); playoffs are excluded. Both official pages are archived as `data/bronze/italy_try0.html` (first leg) and `data/bronze/italy_m_24_25.html` (return leg), and normalized records are deduplicated by official `IdGara` in `data/silver/italy_superlega_m_2024_25.csv`. The audited regular-season slice is 132/132 (100%). This is one season’s regular-season result coverage, not a claim of complete historical or playoff data.

## Backfill from 2000

### CEV 2000/01 parsing correction

The local silver file already contains 20 men's and 20 women's 2000/01 match results from official CEV phase pages (main phase and Final Four). The generated coverage audit previously showed zero women's records because its inventory uses sex `F` and season `2000/01`, while the CEV rows use gender `W` and label `2000/2001`; both values now normalize during coverage aggregation. This repairs the audit count only; the inventory denominator remains blank until the official fixture census is independently reconciled. Reproducible official pages: [men 2000/01 competition overview](https://www-old.cev.eu/Competition-Area/Competition.aspx?ID=70&PID=-2), [men main phase](https://www-old.cev.eu/Competition-Area/Competition.aspx?ID=70&PID=159), [women 2000/01 competition overview](https://www-old.cev.eu/Competition-Area/Competition.aspx?ID=73&PID=-2), [women fixture list](https://www-old.cev.eu/Competition-Area/CompetitionView.aspx?CID=0&ID=73&PID=0&type=LegList), [women main phase](https://www-old.cev.eu/Competition-Area/Competition.aspx?ID=73&PID=167). Counts are source observations, not a completeness percentage.

API-Volleyball supports league/season game queries, but historical depth varies by competition and subscription. The backfill CLI archives each raw season response and writes a per-league/year report through the current UTC year. Obtain IDs from the provider's league endpoint, audit early, middle, and recent seasons, and confirm account entitlement before a full run. A zero-row response is recorded as zero; it does not prove that the season had no matches. The report is raw response coverage, not a complete canonical dataset.

FIVB VIS documents public volleyball match-list requests with date filters and versioning. Public access does not guarantee full coverage back to 2000 or all leagues. Compare each year with official calendars, and account for fields that are not public.

The published open volleyball match-score dataset described in the 2024 Data in Brief article contains 706 matches from selected men's FIVB World Cup editions only (1965–2019, intermittent); it cannot satisfy a 2000-to-current all-league requirement. The CC BY 4.0 file is included as a clearly scoped starter subset under data/. Its source CSV headers are inconsistent, so only the explicit winner field is treated as a usable outcome; other numeric fields remain unverified raw values.
