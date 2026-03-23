"""
Utility helpers for validating pingpartner connectivity via pytest.

The helpers build a target list from the DHCP defaults (dhcp_defaults_v11)
file and use Ansible ad-hoc commands to probe reachability from each host
(or VLAN interface) to its configured pingpartner.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

ANSIBLE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DHCP_DEFAULTS_PATH = ANSIBLE_ROOT / "bootstrapvm/roles/dhcp/defaults/main.yml"
DEFAULT_RESULT_PATH = Path.home() / ".risng" / "pingpartner_results.json"


@dataclass
class PingTarget:
    """Represents one ping check from a host (or NIC) to its partner."""

    name: str
    ansible_host: str
    pingpartner: Optional[str]
    source_label: str


def load_dhcp_defaults(path: Path = DEFAULT_DHCP_DEFAULTS_PATH) -> tuple[Dict, str]:
    """Load the DHCP defaults YAML and return both the parsed data and raw text."""

    raw_text = Path(path).read_text(encoding="utf-8")
    return (yaml.safe_load(raw_text) or {}, raw_text)


PLACEHOLDER_VALUES = {"", "n/a", "na", "none", "null"}


def _normalize_pingpartner_ip(raw_value: Optional[str]) -> Optional[str]:
    """Return a cleaned pingpartner IP or ``None`` for placeholders.

    YAML content may contain placeholder strings (``n/a``) or whitespace-padded
    values. This helper strips known placeholder tokens to avoid spurious
    "no pingpartner configured" results when the DHCP defaults file is
    partially populated.
    """

    if raw_value is None:
        return None

    cleaned = str(raw_value).strip()
    if cleaned.lower() in PLACEHOLDER_VALUES:
        return None

    return cleaned


def _build_pingpartner_lookup(raw_yaml: str) -> Dict[str, str]:
    """Derive a lookup of ip/vlan_ip -> pingpartner_ip from raw YAML text."""

    lookup: Dict[str, str] = {}
    current_ip: Optional[str] = None

    for line in raw_yaml.splitlines():
        stripped = line.strip()
        if stripped.startswith("ip:") or stripped.startswith("vlan_ip:"):
            current_ip = stripped.split(":", 1)[1].strip().strip("\"'")
        elif stripped.startswith("pingpartner_ip:"):
            candidate = _normalize_pingpartner_ip(
                stripped.split(":", 1)[1].strip().strip("\"'")
            )
            if current_ip and candidate:
                lookup[current_ip] = candidate

    return lookup


ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _clean_output(text: str) -> str:
    """Remove ANSI escape sequences and control newlines from log output."""

    return ANSI_ESCAPE_RE.sub("", text).replace("\r", " ").replace("\n", " ").strip()


def build_ping_targets(
    dhcp_defaults: Dict, *, fallback_lookup: Optional[Dict[str, str]] = None
) -> List[PingTarget]:
    """Construct ping targets for base hosts and their extra NICs."""

    targets: List[PingTarget] = []
    for host in dhcp_defaults.get("dhcp_static_hosts", []) or []:
        host_name = host.get("name") or host.get("ip") or "unknown"
        host_ip = host.get("ip")
        pingpartner_ip = _normalize_pingpartner_ip(host.get("pingpartner_ip"))
        if not pingpartner_ip and host_ip and fallback_lookup:
            pingpartner_ip = fallback_lookup.get(str(host_ip))

        if host_ip:
            targets.append(
                PingTarget(
                    name=host_name,
                    ansible_host=str(host_ip),
                    pingpartner=pingpartner_ip,
                    source_label="base",
                )
            )

        for nic in host.get("extra_nics", []) or []:
            vlan_ip = nic.get("vlan_ip")
            if not vlan_ip:
                continue
            nic_pingpartner = _normalize_pingpartner_ip(nic.get("pingpartner_ip"))
            if not nic_pingpartner and fallback_lookup:
                nic_pingpartner = fallback_lookup.get(str(vlan_ip))
            nic_ansible_host = str(host_ip) if host_ip else str(vlan_ip)
            targets.append(
                PingTarget(
                    name=f"{host_name} ({nic.get('mac', 'extra_nic')})",
                    ansible_host=nic_ansible_host,
                    pingpartner=nic_pingpartner,
                    source_label=f"extra_nic:{nic.get('vlan_id', 'n/a')}",
                )
            )

    return targets


def run_pingpartner_healthcheck(
    *,
    dhcp_defaults_path: Path = DEFAULT_DHCP_DEFAULTS_PATH,
    output_path: Path = DEFAULT_RESULT_PATH,
    ansible_binary: str = "ansible",
    ssh_user: str = "root",
    ping_count: int = 1,
    timeout: int = 2,
) -> List[Dict]:
    """Execute ping checks from all DHCP hosts to their pingpartners.

    The function writes a JSON report that can be re-used by pytest and the
    reporting pipeline to colorize the pingpartner column.
    """

    dhcp_defaults, raw_defaults = load_dhcp_defaults(dhcp_defaults_path)
    targets = build_ping_targets(
        dhcp_defaults, fallback_lookup=_build_pingpartner_lookup(raw_defaults)
    )

    results: List[Dict] = []
    tested_at = datetime.now(timezone.utc).isoformat()
    for target in targets:
        if not target.pingpartner:
            results.append(
                {
                    "host": target.name,
                    "ansible_host": target.ansible_host,
                    "pingpartner": None,
                    "source": target.source_label,
                    "status": "missing",
                    "stdout": "",
                    "stderr": "",
                    "tested_at": tested_at,
                }
            )
            continue

        host_pattern = target.ansible_host
        cmd = [
            ansible_binary,
            host_pattern,
            "-i",
            f"{target.ansible_host},",
            "-u",
            ssh_user,
            "-m",
            "ansible.builtin.shell",
            "-a",
            f"ping -c {ping_count} -W {timeout} -q {target.pingpartner}",
        ]

        completed = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
        success = completed.returncode == 0
        cleaned_stdout = _clean_output(completed.stdout)
        cleaned_stderr = _clean_output(completed.stderr)
        results.append(
            {
                "host": target.name,
                "ansible_host": target.ansible_host,
                "pingpartner": target.pingpartner,
                "source": target.source_label,
                "status": "success" if success else "failure",
                "stdout": cleaned_stdout,
                "stderr": cleaned_stderr,
                "tested_at": tested_at,
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = f"# [{tested_at} UTC] generated by risng\n"
    payload = json.dumps(results, indent=2)
    output_path.write_text(f"{header}{payload}", encoding="utf-8")
    return results
