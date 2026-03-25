import json
import os
from pathlib import Path


def _load_summary():
    p = Path(os.environ.get("SUMMARY_FILE", ""))
    assert p.exists(), f"SUMMARY_FILE not found: {p}"
    data = json.loads(p.read_text())
    assert "hosts" in data and isinstance(data["hosts"], list), "summary missing hosts[]"
    return data


def test_summary_has_targets():
    data = _load_summary()
    assert data["hosts"], "No validation targets found in summary"


def test_all_hosts_overall_ok():
    data = _load_summary()
    failed = [h.get("host", "unknown") for h in data["hosts"] if not h.get("overall_ok")]
    assert not failed, f"Non-compliant hosts: {', '.join(failed)}"
