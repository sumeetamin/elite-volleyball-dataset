import os
import requests
from datetime import datetime, timezone
from pathlib import Path
from ..storage import archive_payload, write_manifest
from ..normalize import sha256_bytes

class JsonApiClient:
    def __init__(self, source, base_url, credential_env, root: Path, header="x-apisports-key"):
        token=os.getenv(credential_env)
        if not token: raise RuntimeError(f"Set {credential_env} to enable {source}")
        self.source,self.base_url,self.root,self.token,self.header=source,base_url.rstrip("/"),root,token,header
    def get(self, endpoint, params=None):
        response=requests.get(f"{self.base_url}/{endpoint.lstrip('/')}",params=params,
            headers={self.header:self.token},timeout=(5,30))
        response.raise_for_status()
        content=response.content
        path=archive_payload(self.root,self.source,content,"json")
        digest=sha256_bytes(content)
        write_manifest(self.root/"manifests"/f"{self.source}.jsonl",{
            "source":self.source,"url":response.url,"retrieved_at":datetime.now(timezone.utc).isoformat(),
            "sha256":digest,"bronze_path":str(path)})
        return response.json(),digest
