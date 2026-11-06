import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_plusliga_2010_11_browser_capture.py"
spec = importlib.util.spec_from_file_location("plusliga_2010_11_capture", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_official_2010_11_capture_is_complete_and_valid():
    matches, digest = module.normalize_capture()
    assert len(matches) == 90
    assert len({row["source_match_id"] for row in matches}) == 90
    assert len(digest) == 64
    assert {row["match_date"][:4] for row in matches} == {"2010", "2011"}
