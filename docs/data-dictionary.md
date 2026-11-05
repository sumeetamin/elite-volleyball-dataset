# Canonical data dictionary

Every event record carries source, source_record_id, retrieved_at, and raw_sha256. Times are UTC-aware. Null means unknown or not supplied, never zero. Raw source values remain in bronze and silver rows retain lineage.

| Table | Grain / primary key | Purpose |
|---|---|---|
| matches | source match / match_id | Competition, season, gender, canonical teams, scheduled and played timestamps, status, set result |
| sets | one set / (match_id, set_number) | Actual set points; a completed fifth set uses target 15 |
| team_boxscores | team per match / (match_id, team_id) | Observed action counts and statistic-definition version |
| rallies | rally / (match_id, set_number, rally_number) | Serving team, point winner and score after rally |
| rotations | receiving team per rally / (match_id, team_id, set_number, rally_number) | Setter position and rally result |
| odds | quote snapshot | Provider, match, bookmaker, market, period, selection, decimal price, observed time |
| entity_aliases | provider entity alias | Auditable map to canonical competition/team/player/venue IDs |

Store ratios as derived values in the model project; retain source counts and denominators here. Distinguish source statistic definitions and evaluation-code conventions by version. Do not combine men's/women's or indoor/beach competitions under undocumented rules.
