import json
import os
import sys
import types
from pathlib import Path
from typing import List

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import pytest

# Provide a minimal yaml stub so the helper can be imported without PyYAML.
fake_yaml = types.SimpleNamespace(safe_load=lambda content: json.loads(content))
sys.modules.setdefault("yaml", fake_yaml)

# Ensure local helper module is importable when pytest runs from repo root
sys.path.append(str(Path(__file__).resolve().parent))

from pingpartner_helper_snapshot import (  # noqa: E402
    build_ping_targets,
    run_pingpartner_healthcheck,
)


SAMPLE_DHCP_DEFAULTS = {
    "dhcp_static_hosts": [
        {
            "name": "host-a",
            "ip": "192.168.0.10",
            "pingpartner_ip": "192.168.0.11",
            "extra_nics": [
                {
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "vlan_id": 400,
                    "vlan_ip": "10.0.0.10",
                    "pingpartner_ip": "10.0.0.11",
                }
            ],
        },
        {
            "name": "host-b",
            "ip": "192.168.0.20",
            "extra_nics": [],
        },
        {
            "name": "host-c",
            "ip": "192.168.0.30",
            "pingpartner_ip": " 192.168.0.31 \t",
        },
        {
            "name": "host-d",
            "ip": "192.168.0.40",
            "pingpartner_ip": "n/a",
        },
    ]
}


def test_build_ping_targets_collects_hosts_and_nics():
    targets = build_ping_targets(SAMPLE_DHCP_DEFAULTS)
    assert len(targets) == 5
    assert targets[0].ansible_host == "192.168.0.10"
    assert targets[0].pingpartner == "192.168.0.11"
    assert targets[1].ansible_host == "192.168.0.10"
    assert targets[1].pingpartner == "10.0.0.11"
    assert targets[2].pingpartner is None
    assert targets[3].pingpartner == "192.168.0.31"
    assert targets[4].pingpartner is None


def test_run_pingpartner_healthcheck_writes_json(monkeypatch, tmp_path):
    fake_results: List[str] = []

    class FakeCompleted:
        def __init__(self, cmd):
            fake_results.append(" ".join(cmd))
            self.returncode = 0
            self.stdout = "\u001b[0;33mping ok\u001b[0m\nnext line"
            self.stderr = "\u001b[0;33mwarn\u001b[0m\rmore"

    def fake_run(cmd, capture_output, text, check):
        return FakeCompleted(cmd)

    monkeypatch.setattr("subprocess.run", fake_run)

    defaults_path = tmp_path / "defaults.yml"
    defaults_path.write_text(json.dumps(SAMPLE_DHCP_DEFAULTS))

    output_path = tmp_path / "out.json"
    results = run_pingpartner_healthcheck(
        dhcp_defaults_path=defaults_path,
        output_path=output_path,
        ansible_binary="ansible",
        ping_count=1,
        timeout=1,
    )

    assert output_path.exists()
    stored = output_path.read_text()
    cleaned = "\n".join(
        line for line in stored.splitlines() if not line.lstrip().startswith("#")
    )
    on_disk = json.loads(cleaned)
    assert len(on_disk) == 5
    assert results[0]["status"] == "success"
    assert results[0]["stdout"] == "ping ok next line"
    assert results[0]["stderr"] == "warn more"
    assert results[1]["pingpartner"] == "10.0.0.11"
    assert results[2]["status"] == "missing"
    assert results[3]["pingpartner"] == "192.168.0.31"
    assert results[4]["status"] == "missing"
    assert fake_results[0].startswith("ansible 192.168.0.10 -i 192.168.0.10,")
    assert fake_results[1].startswith("ansible 192.168.0.10 -i 192.168.0.10,")


def test_build_ping_targets_respects_raw_fallback():
    defaults = {
        "dhcp_static_hosts": [
            {
                "name": "fallback-host",
                "ip": "10.0.0.5",
                # Intentionally no pingpartner_ip in parsed data
            }
        ]
    }

    targets = build_ping_targets(defaults, fallback_lookup={"10.0.0.5": "10.0.0.6"})
    assert len(targets) == 1
    assert targets[0].pingpartner == "10.0.0.6"
