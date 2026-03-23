#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path
from pwd import getpwnam
from typing import Dict, List, Optional


def find_matching_brace(text: str, start_index: int) -> Optional[int]:
    depth = 0
    for idx in range(start_index, len(text)):
        ch = text[idx]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return idx
    return None


def extract_block(text: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return None

    brace_start = text.find('{', match.end())
    if brace_start == -1:
        return None

    brace_end = find_matching_brace(text, brace_start)
    if brace_end is None:
        return None

    return text[brace_start + 1: brace_end]


def parse_interfaces(block: str) -> List[Dict[str, object]]:
    interfaces: List[Dict[str, object]] = []
    cursor = 0
    while cursor < len(block):
        match = re.search(r'"?([^"{]+?)"?\s*:[^{]*{', block[cursor:])
        if not match:
            break

        name = match.group(1).strip()
        brace_start = cursor + match.start(0) + match.group(0).rfind('{')
        brace_end = find_matching_brace(block, brace_start)
        if brace_end is None:
            break

        iface_body = block[brace_start + 1: brace_end]
        iface: Dict[str, object] = {"name": name}

        str_fields = ["type", "mac_address", "layer1_standard"]
        for field in str_fields:
            m = re.search(rf'\b{field}\s*:\s*"([^"]*)"', iface_body)
            if m:
                iface[field] = m.group(1)

        ip_match = re.search(r'ip_config\s*:\s*"([^"]+)"', iface_body)
        if ip_match:
            iface["ip_config"] = ip_match.group(1)

        mgmt_match = re.search(r'\bmgmt\s*:\s*true', iface_body, re.IGNORECASE)
        if mgmt_match:
            iface["mgmt"] = True

        interfaces.append(iface)
        cursor = brace_end + 1

    return interfaces


def parse_devices(content: str) -> List[Dict[str, object]]:
    devices_section = extract_block(content, r'\bdevices\s*:')
    if devices_section is None:
        return []

    devices: List[Dict[str, object]] = []
    cursor = 0
    while cursor < len(devices_section):
        match = re.search(r'([A-Za-z0-9_.-]+)\s*:[^{]*{', devices_section[cursor:])
        if not match:
            break

        hostname = match.group(1)
        brace_start = cursor + match.start(0) + match.group(0).rfind('{')
        brace_end = find_matching_brace(devices_section, brace_start)
        if brace_end is None:
            break

        device_body = devices_section[brace_start + 1: brace_end]
        device: Dict[str, object] = {"hostname": hostname}

        string_fields = [
            "dell_expresscode",
            "dell_servicetag",
            "device_role",
            "dfs_asset_number",
            "dfs_equipment_number",
            "cluster",
        ]
        for field in string_fields:
            m = re.search(rf'\b{field}\s*:\s*"([^"]*)"', device_body)
            if m:
                device[field] = m.group(1)

        rack_match = re.search(r'rack_position\s*:\s*([0-9]+)', device_body)
        if rack_match:
            device["rack_position"] = int(rack_match.group(1))

        interfaces_block = extract_block(device_body, r'network_config\s*:\s*interfaces\s*:')
        if interfaces_block:
            device["interfaces"] = parse_interfaces(interfaces_block)

        devices.append(device)
        cursor = brace_end + 1

    return devices


def parse_cue_file(path: Path) -> List[Dict[str, object]]:
    content = path.read_text(encoding="utf-8")
    package_match = re.search(r'^\s*package\s+([\w.-]+)', content, re.MULTILINE)
    package_name = package_match.group(1) if package_match else None

    records = []
    for device in parse_devices(content):
        if package_name:
            device["package"] = package_name
        device["source_file"] = str(path)
        records.append(device)
    return records


def ensure_owner(path: Path) -> None:
    target_uid = os.getuid()
    target_gid = os.getgid()

    if os.geteuid() == 0:
        sudo_uid = os.environ.get("SUDO_UID")
        sudo_gid = os.environ.get("SUDO_GID")
        sudo_user = os.environ.get("SUDO_USER")

        if sudo_uid and sudo_gid:
            target_uid = int(sudo_uid)
            target_gid = int(sudo_gid)
        elif sudo_user:
            user_info = getpwnam(sudo_user)
            target_uid = user_info.pw_uid
            target_gid = user_info.pw_gid

    if (path.stat().st_uid, path.stat().st_gid) != (target_uid, target_gid):
        try:
            os.chown(path, target_uid, target_gid)
        except OSError:
            pass


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(
            "Usage: inventory_import.py <inventory_repo> <output_json> [<dhcp_output>]",
            file=sys.stderr,
        )
        return 1

    repo_path = Path(sys.argv[1]).expanduser().resolve()
    output_path = Path(sys.argv[2]).expanduser().resolve()
    dhcp_output = (
        Path(sys.argv[3]).expanduser().resolve()
        if len(sys.argv) == 4
        else Path(os.environ.get("HOME", str(Path.home()))).expanduser().resolve()
        / "dhcp_enriched.yml"
    )

    if not repo_path.is_dir():
        print(f"Inventory repository not found: {repo_path}", file=sys.stderr)
        return 1

    all_records: List[Dict[str, object]] = []
    for cue_file in sorted(repo_path.rglob("*.cue")):
        all_records.extend(parse_cue_file(cue_file))

    output_path.write_text(json.dumps(all_records, indent=2, ensure_ascii=False), encoding="utf-8")
    ensure_owner(output_path)

    dhcp_template_path = Path(__file__).resolve().parents[2] / "bootstrapvm/roles/dhcp/defaults/main.yml"

    template_text = ""
    if dhcp_template_path.exists():
        template_text = dhcp_template_path.read_text(encoding="utf-8")

    def to_yaml_block(data: Dict[str, object]) -> str:
        lines = [f"  - name: {data.get('name', 'n/a')}"]
        lines.append(f"    mac: \"{data.get('mac', 'n/a')}\"")
        lines.append(f"    ip: \"{data.get('ip', 'n/a')}\"")
        lines.append(f"    pingpartner_ip: \"{data.get('pingpartner_ip', 'n/a')}\"")

        extras = data.get("extra_nics") or []
        if extras:
            lines.append("    extra_nics:")
            for nic in extras:
                lines.append(f"      - mac: \"{nic.get('mac', 'n/a')}\"")
                lines.append(f"        vlan_id: \"{nic.get('vlan_id', 'n/a')}\"")
                lines.append(f"        vlan_ip: \"{nic.get('vlan_ip', 'n/a')}\"")
                lines.append(f"        pingpartner_ip: \"{nic.get('pingpartner_ip', 'n/a')}\"")

        return "\n".join(lines)

    enriched_blocks: List[str] = []
    for record in all_records:
        interfaces = record.get("interfaces") or []
        primary_iface = next((iface for iface in interfaces if iface.get("mgmt")), interfaces[0] if interfaces else None)

        primary_mac = "n/a"
        primary_ip = "n/a"
        if primary_iface:
            primary_mac = primary_iface.get("mac_address", "n/a") or "n/a"
            ip_config = primary_iface.get("ip_config")
            if ip_config:
                primary_ip = ip_config.split("/")[0]

        host_entry: Dict[str, object] = {
            "name": record.get("hostname", "n/a"),
            "mac": primary_mac,
            "ip": primary_ip,
            "pingpartner_ip": "n/a",
        }

        extra_nics: List[Dict[str, object]] = []
        for iface in interfaces:
            if iface is primary_iface:
                continue

            vlan_ip = "n/a"
            if iface.get("ip_config"):
                vlan_ip = iface["ip_config"].split("/")[0]

            extra_nics.append(
                {
                    "mac": iface.get("mac_address", "n/a") or "n/a",
                    "vlan_id": "n/a",
                    "vlan_ip": vlan_ip,
                    "pingpartner_ip": "n/a",
                }
            )

        if extra_nics:
            host_entry["extra_nics"] = extra_nics

        enriched_blocks.append(to_yaml_block(host_entry))

    header = "# Generated hosts from inventory-import\n"
    combined = template_text.rstrip() + "\n\n" + header + "\n".join(enriched_blocks) + "\n"
    dhcp_output.write_text(combined, encoding="utf-8")
    ensure_owner(dhcp_output)

    print(
        f"Wrote {len(all_records)} records to {output_path} and "
        f"generated DHCP data in {dhcp_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
