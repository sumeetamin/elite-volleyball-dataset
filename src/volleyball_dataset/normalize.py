"""Stable source identifiers and timestamp/hash normalization."""
import hashlib
import json
import pandas as pd

def stable_match_id(source: str, source_match_id: str) -> str:
    if not source_match_id:
        raise ValueError("source match ID required; never infer identity from team names/date")
    return f"{source.upper()}_{source_match_id}"

def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def to_utc(value):
    if value is None or pd.isna(value): return None
    stamp = pd.Timestamp(value)
    if stamp.tzinfo is None:
        raise ValueError("naive timestamp: source timezone must be explicit")
    return stamp.tz_convert("UTC")

def canonical_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
