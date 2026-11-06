# Elite Volleyball Dataset

Versioned data pipeline for volleyball match results, observed box scores, rallies, rotations, and timestamped odds. Raw source payloads are immutable; normalized records retain source provenance. Missing data stays null. Estimated data is never represented as observed data.

## Quick start

Python 3.11+ is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
python -m volleyball_dataset.cli validate --config config/sources.yml
```

Configure a source only after confirming its league/season coverage, permitted use, and sample response. Set credentials in environment variables, never in config or Git.

## Data layers

- `bronze/`: source response/file, retrieval timestamp, hash, provider ID.
- `silver/`: normalized entities and event tables with source lineage.
- `gold/`: prediction-cutoff feature snapshots and coverage reports.
- `quarantine/`: invalid or unresolved rows requiring review.

Local outputs default to `data/` (gitignored); use a versioned object store for releases. This repo contains schemas and pipeline code, not private scouting files or fabricated records.

## Sources

FIVB VIS for international schedules/results and public reports; official league sites for competition records; API-Volleyball only for explicitly audited coverage; authorized DataVolley `.dvw` files parsed through OpenVolley/py-datavolley; odds providers only after confirming volleyball coverage and terms. The Odds API is not assumed to cover volleyball. See `docs/source-audit.md`.

## Historical coverage work

The target competition-season scope and its official denominator checklist are in `config/competition_seasons.csv`; source endpoints and known limitations are in `config/source_registry.csv`. `volley-data coverage` generates `data/coverage_audit.csv`. It intentionally leaves a percentage blank until the official expected match count is entered for that competition-season. Run `volley-data import-cbv` after downloading CBV Data Project `CompetitionMatches.aspx?ID=...` pages into `data/bronze/`. Scheduled GitHub Actions refreshes FIVB results and rebuilds the coverage audit daily; this does not automatically fill historical club-league gaps.

The CBV adapter identifies regular-season rows by their parent phase and records all unique fixture IDs, including fixtures with no posted score. `data/coverage/cbv_seasons.csv` reports completed-result coverage against the enumerated regular-phase IDs in each captured official page, with the raw-page hash for audit. A match with no final score is retained as `unknown`, never counted as a completed result. Playoffs are retained as a separate phase and excluded from regular-season coverage.

CBV's 2024/25 regulations specify 12 teams playing a double round robin, then best-of-three quarterfinals and semifinals and a single final. The 2017/18–2024/25 archived pages each enumerate 132 regular-season IDs, except the 2022/23 women's page with 133. Keep that observed anomaly documented instead of normalizing it to the expected format. The 2019/20 men's schedule includes six fixtures without results, consistent with the pandemic interruption; those remain in the denominator and outside the completed-result numerator.
