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
