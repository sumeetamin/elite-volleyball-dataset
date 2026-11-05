"""Read-only transport for documented public FIVB VIS XML requests."""
from datetime import datetime, timezone
from pathlib import Path
import requests
from ..normalize import sha256_bytes
from ..storage import archive_payload, write_manifest

class FivbVis:
    endpoint="https://www.fivb.org/Vis2009/XmlRequest.asmx"
    def __init__(self,root:Path): self.root=root
    def request(self,request_name,**fields):
        response=requests.get(self.endpoint,params={"Request":request_name,**fields},timeout=(5,30))
        response.raise_for_status()
        content=response.content
        path=archive_payload(self.root,"fivb_vis",content,"xml")
        digest=sha256_bytes(content)
        write_manifest(self.root/"manifests"/"fivb_vis.jsonl",{
            "request":request_name,"retrieved_at":datetime.now(timezone.utc).isoformat(),
            "sha256":digest,"bronze_path":str(path)})
        return content
