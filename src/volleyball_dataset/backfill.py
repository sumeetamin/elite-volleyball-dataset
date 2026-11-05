"""Auditable season-by-season raw history backfill for API-Volleyball."""
from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .sources.apisports import ApiVolleyball
from .storage import write_manifest

def backfill_api_volleyball(root: Path, league_ids: list[str], start_year: int = 2000,
                            end_year: int | None = None, delay_seconds: float = 0.3) -> pd.DataFrame:
    """Fetch configured league seasons and save raw responses plus coverage report."""
    end_year = end_year or datetime.now(timezone.utc).year
    if start_year < 1900 or end_year < start_year: raise ValueError("invalid year range")
    client = ApiVolleyball(root)
    results=[]
    for league_id in league_ids:
        for year in range(start_year,end_year+1):
            try:
                payload,digest=client.get("games",{"league":league_id,"season":year})
                response=payload.get("response",[]) if isinstance(payload,dict) else []
                errors=payload.get("errors",{}) if isinstance(payload,dict) else {}
                record={"provider":"api_volleyball","league_id":str(league_id),"season":year,
                        "retrieved_at":datetime.now(timezone.utc).isoformat(),"raw_sha256":digest,
                        "records_returned":len(response),"provider_errors":json.dumps(errors,sort_keys=True),
                        "status":"ok" if not errors else "provider_error"}
            except Exception as exc:
                record={"provider":"api_volleyball","league_id":str(league_id),"season":year,
                        "retrieved_at":datetime.now(timezone.utc).isoformat(),"records_returned":0,
                        "status":"request_failed","error":str(exc)}
            write_manifest(root/"manifests"/"season_backfill.jsonl",record)
            results.append(record)
            time.sleep(delay_seconds)
    report=pd.DataFrame(results)
    root.mkdir(parents=True,exist_ok=True)
    report.to_csv(root/"coverage_api_volleyball.csv",index=False)
    return report
