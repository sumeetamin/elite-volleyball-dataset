"""Transport for documented public FIVB VIS XML requests."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from ..normalize import sha256_bytes
from ..storage import archive_payload, write_manifest

class FivbVis:
    endpoint = "https://www.fivb.org/Vis2009/XmlRequest.asmx"
    def __init__(self, root: Path): self.root = root

    def request_xml(self, request_xml: str, label: str = "request") -> bytes:
        body = urlencode({"Request": request_xml}).encode("utf-8")
        req = Request(self.endpoint, data=body, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/xml",
            "User-Agent": "elite-volleyball-dataset/0.1 (public historical results research)",
        })
        with urlopen(req, timeout=60) as response:
            content = response.read()
            status = response.status
        path = archive_payload(self.root, "fivb_vis", content, "xml")
        digest = sha256_bytes(content)
        write_manifest(self.root / "manifests" / "fivb_vis.jsonl", {
            "label": label, "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "status": status, "sha256": digest, "bronze_path": str(path),
        })
        return content
