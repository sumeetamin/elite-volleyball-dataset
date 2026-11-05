import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def archive_payload(root: Path, source: str, payload: bytes, suffix: str = "json") -> Path:
    """Write immutable content-addressed bronze data and return its path."""
    digest = hashlib.sha256(payload).hexdigest()
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    target = root / "bronze" / source / day / f"{digest}.{suffix}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(payload)
    return target


def write_manifest(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
