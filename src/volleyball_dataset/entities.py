"""Canonical identity resolution with explicit, reviewable aliases."""
import re
import unicodedata
import pandas as pd

def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()

class EntityResolver:
    def __init__(self, aliases: pd.DataFrame):
        required = {"source", "entity_type", "source_id", "source_name", "canonical_id"}
        if not required.issubset(aliases.columns):
            raise ValueError(f"aliases missing columns: {sorted(required - set(aliases.columns))}")
        self.aliases = aliases.copy()
        self.aliases["normalized_name"] = self.aliases.source_name.map(normalize_name)

    def resolve(self, source: str, entity_type: str, source_id: str | None, name: str) -> str:
        rows = self.aliases[(self.aliases.source == source) & (self.aliases.entity_type == entity_type)]
        if source_id:
            exact = rows[rows.source_id.astype(str) == str(source_id)]
            if len(exact) == 1: return str(exact.iloc[0].canonical_id)
            if len(exact) > 1: raise ValueError(f"ambiguous source ID: {source}/{entity_type}/{source_id}")
        ids = rows[rows.normalized_name == normalize_name(name)].canonical_id.unique()
        if len(ids) == 1: return str(ids[0])
        if len(ids) > 1: raise ValueError(f"ambiguous entity name: {source}/{entity_type}/{name}")
        raise LookupError(f"unresolved entity: {source}/{entity_type}/{source_id}/{name}")
