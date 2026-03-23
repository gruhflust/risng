#!/usr/bin/env python3
"""Convert report.json into a styled PDF and HTML overview."""
from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

# PDF layout (A4 landscape)
PAGE_WIDTH = 842  # width in points
PAGE_HEIGHT = 595  # height in points
MARGIN = 36
FONT_SIZE = 7
LINE_HEIGHT = 11

# Table layout (character widths for PDF rendering)
TABLE_COLUMNS = [
    ("Hostname", 18),
    ("hostname assigned", 20),
    ("PXE-Mac Address", 18),
    ("SSH Reachable", 10),
    ("System Volume", 16),
    ("Network Adapters", 44),
    ("pingpartner", 10),
    ("pingpartner success", 20),
]
TABLE_DIVIDER = "+" + "+".join("-" * (width + 2) for _, width in TABLE_COLUMNS) + "+"
TABLE_HEADER_DIVIDER = "+" + "+".join("=" * (width + 2) for _, width in TABLE_COLUMNS) + "+"
CARD_WIDTH = len(TABLE_DIVIDER)
MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def _default_pingpartner_path() -> Path:
    base_path = Path(__file__).resolve()
    try:
        return (base_path.parents[3] / "bootstrapvm/roles/dhcp/defaults/main.yml").resolve()
    except IndexError:
        return (base_path.parent / "../bootstrapvm/roles/dhcp/defaults/main.yml").resolve()


PINGPARTNER_DEFAULTS_PATH = _default_pingpartner_path()


def _find_defaults_path() -> Optional[Path]:
    """Locate the DHCP defaults file regardless of where the script lives.

    The playbook copies this script to ``/tmp`` before executing it, so the
    original relative path from ``__file__`` may not exist anymore. To keep the
    pingpartner extraction functional, probe a handful of likely locations,
    including the current working directory and its parents.
    """

    env_override = os.environ.get("PINGPARTNER_DEFAULTS_PATH")
    if env_override:
        candidate = Path(env_override).expanduser().resolve()
        if candidate.exists():
            return candidate

    rel_paths = [
        Path("../bootstrapvm/roles/dhcp/defaults/main.yml"),
        Path("../ansible/bootstrapvm/roles/dhcp/defaults/main.yml"),
        Path("risng_code/ansible/bootstrapvm/roles/dhcp/defaults/main.yml"),
        Path("code/ansible/bootstrapvm/roles/dhcp/defaults/main.yml"),
        Path("bootstrapvm/roles/dhcp/defaults/main.yml"),
    ]

    probe_roots = list(dict.fromkeys([Path(__file__).resolve().parent, Path.cwd()] + list(Path(__file__).resolve().parents) + list(Path.cwd().parents)))
    for root in probe_roots:
        for rel in rel_paths:
            candidate = (root / rel).resolve()
            if candidate.exists():
                return candidate

    if PINGPARTNER_DEFAULTS_PATH.exists():
        return PINGPARTNER_DEFAULTS_PATH
    return None


class PingpartnerCache:
    def __init__(self) -> None:
        self.by_ip: dict[str, List[str]] | None = None
        self.by_mac: dict[str, List[str]] | None = None

    def _normalize_mac(self, value: Optional[str]) -> str:
        value = (value or "").strip().lower()
        value = re.sub(r"[^0-9a-f]", "", value)
        if len(value) == 12:
            value = ":".join(value[i : i + 2] for i in range(0, 12, 2))
        return value

    def _add_partner(self, mapping: dict[str, List[str]], key: str, partner: str) -> None:
        if not key or not partner:
            return
        if partner.lower() == "n/a":
            return
        if partner not in mapping.setdefault(key, []):
            mapping[key].append(partner)

    def load(self, defaults_path: Optional[Path] = None) -> None:
        if self.by_ip is not None and self.by_mac is not None:
            return

        self.by_ip = {}
        self.by_mac = {}

        defaults_path = defaults_path or _find_defaults_path()
        if not defaults_path:
            return

        try:
            lines = defaults_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return

        current_ip: Optional[str] = None
        current_mac: Optional[str] = None

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                continue

            if stripped.startswith("- name:"):
                current_ip = None
                current_mac = None
                continue

            if stripped.startswith("ip:") or stripped.startswith("vlan_ip:"):
                current_ip = stripped.split(":", 1)[1].strip().strip("\"'")
                continue

            if stripped.startswith("mac:"):
                current_mac = self._normalize_mac(stripped.split(":", 1)[1])
                continue

            if stripped.startswith("pingpartner_ip:"):
                partner_val = stripped.split(":", 1)[1].strip()
                if "#" in partner_val:
                    partner_val = partner_val.split("#", 1)[0].rstrip()
                partner_val = partner_val.strip("\"'")
                if current_ip:
                    self._add_partner(self.by_ip, current_ip, partner_val)
                if current_mac:
                    self._add_partner(self.by_mac, current_mac, partner_val)

    def for_entry(self, entry: dict) -> List[str]:
        if self.by_ip is None or self.by_mac is None:
            self.load()

        partners: List[str] = []
        seen = set()

        def extend_with(values: Optional[Sequence[str]]) -> None:
            for value in values or []:
                if value in seen:
                    continue
                seen.add(value)
                partners.append(value)

        ip = (entry.get("ip") or "").strip()
        mac = self._normalize_mac(entry.get("mac"))

        if self.by_ip and ip in self.by_ip:
            extend_with(self.by_ip[ip])
        if self.by_mac and mac in self.by_mac:
            extend_with(self.by_mac[mac])

        return partners


PINGPARTNER_CACHE = PingpartnerCache()
PINGPARTNER_RESULTS_ENV = "PINGPARTNER_RESULTS_PATH"
PINGPARTNER_ARCHIVE_ENV = "PINGPARTNER_ARCHIVE_DIR"


def _strip_json_comments(content: str) -> str:
    """Remove lines starting with a '#', which we use for timestamp headers."""

    return "\n".join(
        line for line in content.splitlines() if not line.lstrip().startswith("#")
    )


def _resolve_pingpartner_results_path(path: Optional[Path] = None) -> Path:
    env_path = os.environ.get(PINGPARTNER_RESULTS_ENV)
    if env_path:
        return Path(env_path).expanduser()
    candidates: List[Path] = []
    if path:
        candidates.append(Path(path).expanduser())

    home_env = os.environ.get("HOME")
    if home_env:
        candidates.append(Path(home_env).expanduser() / "test_results.json")
    candidates.append(Path.home() / "test_results.json")
    candidates.append(Path("/home/risng/test_results.json"))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if candidates:
        return candidates[0]
    return Path("test_results.json")


def _resolve_pingpartner_archive_dir(path: Optional[Path] = None) -> Path:
    env_path = os.environ.get(PINGPARTNER_ARCHIVE_ENV)
    if env_path:
        return Path(env_path).expanduser()
    if path:
        return Path(path).expanduser()
    return Path.home() / "reportcollection"


def _parse_timestamp(value: str) -> Optional[datetime]:
    cleaned = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _is_newer(candidate: Optional[str], reference: Optional[str]) -> bool:
    if candidate and not reference:
        return True
    candidate_ts = _parse_timestamp(candidate) if candidate else None
    reference_ts = _parse_timestamp(reference) if reference else None
    if candidate_ts and reference_ts:
        return candidate_ts > reference_ts
    return bool(candidate) and not reference


def _load_pingpartner_archives(directory: Optional[Path] = None) -> dict[str, dict]:
    archive_dir = _resolve_pingpartner_archive_dir(directory)
    if not archive_dir.exists() or not archive_dir.is_dir():
        return {}

    successes: dict[str, dict] = {}
    for path in sorted(archive_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(payload, dict):
            continue
        partner = str(payload.get("pingpartner") or "").strip()
        status = str(payload.get("status") or "").strip().lower()
        tested_at = str(payload.get("tested_at") or "").strip()
        if status != "success" or not partner:
            continue

        existing = successes.get(partner)
        if existing is None or _is_newer(tested_at, existing.get("tested_at")):
            successes[partner] = {"status": "success", "tested_at": tested_at or None}

    return successes


def load_pingpartner_results(
    path: Optional[Path] = None, archive_dir: Optional[Path] = None
) -> dict[str, dict]:
    result_path = _resolve_pingpartner_results_path(path)
    try:
        content = result_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return _load_pingpartner_archives(archive_dir)
    except OSError:
        return _load_pingpartner_archives(archive_dir)

    try:
        payload = json.loads(_strip_json_comments(content))
    except json.JSONDecodeError:
        return _load_pingpartner_archives(archive_dir)

    if not isinstance(payload, list):
        return _load_pingpartner_archives(archive_dir)

    priority = {"success": 2, "failure": 1, "missing": 0}
    statuses: dict[str, dict] = _load_pingpartner_archives(archive_dir)
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        partner = str(entry.get("pingpartner") or "").strip()
        status = str(entry.get("status") or "").strip().lower()
        tested_at = str(entry.get("tested_at") or "").strip() or None
        if not partner or not status:
            continue

        current = statuses.get(partner)
        if status == "success":
            if current is None or current.get("status") != "success" or _is_newer(
                tested_at, current.get("tested_at")
            ):
                statuses[partner] = {"status": status, "tested_at": tested_at}
            continue

        if current is None or priority.get(status, -1) > priority.get(
            current.get("status"), -1
        ):
            statuses[partner] = {"status": status, "tested_at": tested_at}

    return statuses


def usage() -> None:
    print(
        "Usage: report_to_pdf.py <input.json> <output.pdf>",
        "\n\nThe script also creates a matching HTML report next to the PDF output.",
        sep="",
        file=sys.stderr,
    )


def load_report(path: str) -> Sequence[dict]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Report JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Report JSON is invalid: {exc}") from exc

    if not isinstance(data, list):
        raise SystemExit("Report JSON must contain a list of host entries.")
    return data


def normalize_hostname(entry: dict) -> str:
    hostname = (entry.get("hostname") or "").strip()
    if hostname:
        return hostname
    ip = (entry.get("ip") or "").strip()
    return ip or "Unknown"


IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b")


def normalize_interfaces(
    raw_interfaces: Iterable[object], lease_ip: Optional[str] = None
) -> List[str]:
    interfaces = []
    has_ip_info = False
    lease_ip = (lease_ip or "").strip()
    for raw in raw_interfaces or []:
        if isinstance(raw, str):
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            name = parts[0]
            mac = None
            addr_tokens = []
            for token in parts[1:]:
                token = token.strip().strip("<>")
                if MAC_RE.fullmatch(token):
                    mac = token.lower()
                    break
                if IP_RE.search(token):
                    addr_tokens.append(token)
            if name == "lo" or mac == "00:00:00:00:00:00":
                continue
            label = f"{name} ({mac or 'n/a'})"
            if addr_tokens:
                has_ip_info = True
                label += " – " + ", ".join(addr_tokens)
            interfaces.append(label)
            continue

        if isinstance(raw, dict):
            name = (raw.get("ifname") or raw.get("name") or "").strip()
            mac = (raw.get("address") or raw.get("mac") or "").strip() or None
            if mac:
                mac = mac.lower()
            if not name or name == "lo" or mac == "00:00:00:00:00:00":
                continue

            ip_addrs: List[str] = []
            for addr in raw.get("addr_info") or []:
                local = (addr.get("local") or "").strip()
                if not local:
                    continue
                has_ip_info = True
                prefix = addr.get("prefixlen")
                if prefix is not None:
                    ip_addrs.append(f"{local}/{prefix}")
                else:
                    ip_addrs.append(local)

            label = f"{name} ({mac or 'n/a'})"
            if ip_addrs:
                label += " – " + ", ".join(ip_addrs)
            interfaces.append(label)

    if not has_ip_info and lease_ip:
        interfaces.append(f"DHCP lease IP: {lease_ip}")

    return interfaces


def normalize_pingpartners(entry: dict) -> List[str]:
    partners = entry.get("pingpartners")
    normalized: List[str] = []
    seen = set()

    def add(value: object) -> None:
        if value is None:
            return
        text = str(value).strip()
        if not text or text.lower() == "n/a":
            return
        if text in seen:
            return
        seen.add(text)
        normalized.append(text)

    if isinstance(partners, (list, tuple)):
        for partner in partners:
            add(partner)
    else:
        add(entry.get("pingpartner"))

    return normalized


def supplement_pingpartners(entry: dict, existing: List[str]) -> List[str]:
    if existing:
        return existing
    fallback = PINGPARTNER_CACHE.for_entry(entry)
    return existing + fallback if fallback else existing


def format_test_timestamp(value: Optional[str]) -> str:
    if not value:
        return ""
    parsed = _parse_timestamp(value)
    if not parsed:
        return value
    parsed = parsed.astimezone(timezone.utc)
    return parsed.strftime("%Y-%m-%d %H:%M UTC")


def format_pingpartner(partners: Sequence[str]) -> str:
    if not partners:
        return "n/a"
    return ", ".join(partners)


def linkify_ips(text: str) -> str:
    """Convert IPv4 occurrences inside *text* into clickable SSH commands.

    The anchor text keeps any CIDR suffix while the link target strips it so the
    SSH command uses the plain address.
    """

    pieces: List[str] = []
    cursor = 0
    for match in IP_RE.finditer(text):
        plain_chunk = text[cursor : match.start()]
        ip_with_suffix = match.group()
        ip = ip_with_suffix.split("/", 1)[0]
        pieces.append(html.escape(plain_chunk))
        ssh_cmd = f"/usr/bin/ssh root@{ip}"
        pieces.append(
            f"<a class=\"ip-link\" href=\"{html.escape(ssh_cmd)}\" title=\"{html.escape(ssh_cmd)}\">{html.escape(ip_with_suffix)}"  # noqa: E501
            "</a>"
        )
        cursor = match.end()

    pieces.append(html.escape(text[cursor:]))
    return "".join(pieces)


def format_system_volume(entry: dict) -> str:
    disks = entry.get("disks") or []
    formatted_disks: List[str] = []

    for disk in disks:
        if not isinstance(disk, dict):
            continue

        size_gb = disk.get("size_gb")
        size_bytes = disk.get("bytes")
        label = (disk.get("name") or "").strip()

        size_str: Optional[str]
        if isinstance(size_gb, (int, float)):
            size_str = f"{float(size_gb):.1f} GB"
        elif isinstance(size_bytes, (int, float)):
            size_str = f"{float(size_bytes) / 1073741824:.1f} GB"
        else:
            size_str = None

        if size_str and label:
            formatted_disks.append(f"{label} • {size_str}")
        elif size_str:
            formatted_disks.append(size_str)
        elif label:
            formatted_disks.append(label)

    if not formatted_disks:
        return "n/a"

    return ", ".join(formatted_disks)


def build_host_data(
    entries: Sequence[dict], pingpartner_results: Optional[dict[str, dict]] = None
) -> List[dict]:
    pingpartner_results = pingpartner_results or {}
    hosts: List[dict] = []
    for entry in entries:
        host = normalize_hostname(entry)
        mac = (
            entry.get("mac")
            or entry.get("lease_mac_normalized")
            or "-"
        ).strip() or "-"
        assigned = (
            entry.get("dhcp_assigned_hostname")
            or entry.get("lease_hostname")
            or ""
        ).strip() or "—"
        ping_partners = supplement_pingpartners(entry, normalize_pingpartners(entry))
        ping_partner = format_pingpartner(ping_partners)
        reachable_flag = bool(entry.get("ssh_ok"))
        reachable = "Yes" if reachable_flag else "No"
        interfaces = normalize_interfaces(entry.get("interfaces") or [], entry.get("ip"))
        pingpartner_status: dict[str, str] = {}
        success_timestamps: List[str] = []
        for partner in ping_partners:
            result_info = pingpartner_results.get(partner) or {}
            status_value = result_info.get("status") if isinstance(result_info, dict) else result_info
            if status_value:
                pingpartner_status[partner] = status_value
            if str(status_value).lower() == "success":
                formatted = format_test_timestamp(result_info.get("tested_at") if isinstance(result_info, dict) else None)
                label = formatted if formatted else "success"
                success_timestamps.append(f"{label} ({partner})")
        hosts.append(
            {
                "host": host,
                "assigned": assigned,
                "mac": mac,
                "reachable": reachable,
                "reachable_flag": reachable_flag,
                "interfaces": interfaces,
                "system_volume": format_system_volume(entry),
                "pingpartners": ping_partners,
                "pingpartner": ping_partner,
                "pingpartner_status": pingpartner_status,
                "pingpartner_success": ", ".join(success_timestamps) if success_timestamps else "—",
                "pingpartner_success_list": success_timestamps,
            }
        )
    hosts.sort(key=lambda item: item["host"].lower())
    return hosts


def build_metadata(hosts: Sequence[dict], generated_at: datetime) -> dict:
    timestamp = generated_at.strftime("%Y-%m-%d %H:%M:%S")
    timestamp_iso = generated_at.isoformat(timespec="seconds")
    total = len(hosts)
    reachable = sum(1 for host in hosts if host.get("reachable_flag"))
    return {
        "title": "RISng Client Report",
        "subtitle": "The listed clients were intended to be tested through RISng.",
        "timestamp": timestamp,
        "timestamp_iso": timestamp_iso,
        "generated_at": generated_at,
        "total": total,
        "reachable": reachable,
        "unreachable": max(0, total - reachable),
    }


def _wrap_simple_cell(value: str, width: int) -> List[str]:
    content = (value or "").strip()
    wrapper = textwrap.TextWrapper(
        width=width,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=False,
    )
    lines = wrapper.wrap(content)
    return lines or [""]


def _wrap_interface_cell(interfaces: Sequence[str], width: int) -> List[str]:
    if not interfaces:
        return ["—"]

    wrapped: List[str] = []
    bullet = "• "
    bullet_width = len(bullet)
    inner_width = max(1, width - bullet_width)
    wrapper = textwrap.TextWrapper(
        width=inner_width,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=False,
    )

    for item in interfaces:
        chunks = wrapper.wrap(item)
        if not chunks:
            wrapped.append(bullet.rstrip())
            continue
        wrapped.append(bullet + chunks[0])
        wrapped.extend(" " * bullet_width + chunk for chunk in chunks[1:])
    return wrapped or ["—"]


def _format_table_line(parts: Sequence[str]) -> str:
    padded = [f"{value:<{width}}" for value, (_, width) in zip(parts, TABLE_COLUMNS)]
    return "| " + " | ".join(padded) + " |"


def build_pdf_table(hosts: Sequence[dict]) -> List[str]:
    if not hosts:
        return []

    lines: List[str] = [TABLE_DIVIDER]
    header = [name.upper() for name, _ in TABLE_COLUMNS]
    lines.append(_format_table_line(header))
    lines.append(TABLE_HEADER_DIVIDER)

    for host in hosts:
        host_lines = _wrap_simple_cell(host["host"], TABLE_COLUMNS[0][1])
        assigned_lines = _wrap_simple_cell(host["assigned"], TABLE_COLUMNS[1][1])
        mac_lines = _wrap_simple_cell(host["mac"], TABLE_COLUMNS[2][1])
        reachable_lines = _wrap_simple_cell(host["reachable"], TABLE_COLUMNS[3][1])
        volume_lines = _wrap_simple_cell(host.get("system_volume", ""), TABLE_COLUMNS[4][1])
        interface_lines = _wrap_interface_cell(host.get("interfaces") or [], TABLE_COLUMNS[5][1])
        pingpartner_lines = _wrap_simple_cell(host.get("pingpartner", ""), TABLE_COLUMNS[6][1])
        pingpartner_success_lines = _wrap_simple_cell(
            host.get("pingpartner_success", ""), TABLE_COLUMNS[7][1]
        )

        max_lines = max(
            len(host_lines),
            len(assigned_lines),
            len(mac_lines),
            len(reachable_lines),
            len(volume_lines),
            len(interface_lines),
            len(pingpartner_lines),
            len(pingpartner_success_lines),
        )
        for index in range(max_lines):
            row_parts = [
                host_lines[index] if index < len(host_lines) else "",
                assigned_lines[index] if index < len(assigned_lines) else "",
                mac_lines[index] if index < len(mac_lines) else "",
                reachable_lines[index] if index < len(reachable_lines) else "",
                volume_lines[index] if index < len(volume_lines) else "",
                interface_lines[index] if index < len(interface_lines) else "",
                pingpartner_lines[index] if index < len(pingpartner_lines) else "",
                pingpartner_success_lines[index]
                if index < len(pingpartner_success_lines)
                else "",
            ]
            lines.append(_format_table_line(row_parts))
        lines.append(TABLE_DIVIDER)

    return lines


def _card_line(text: str, width: int, *, align: str = "left") -> str:
    inner = width - 4
    if align == "center":
        content = text.center(inner)
    else:
        content = text.ljust(inner)
    return f"║ {content} ║"


def build_pdf_lines(hosts: Sequence[dict], metadata: dict) -> List[str]:
    lines: List[str] = []

    title = metadata.get("title", "RISng Client Report")
    subtitle = metadata.get(
        "subtitle",
        "The listed clients were intended to be tested through RISng.",
    )
    total = metadata.get("total", len(hosts))
    reachable = metadata.get("reachable", 0)
    unreachable = metadata.get("unreachable", max(0, total - reachable))
    timestamp = metadata.get("timestamp", "-")

    lines.append("╔" + "═" * (CARD_WIDTH - 2) + "╗")
    lines.append(_card_line(title, CARD_WIDTH, align="center"))
    lines.append(_card_line(subtitle, CARD_WIDTH, align="center"))
    lines.append("╠" + "═" * (CARD_WIDTH - 2) + "╣")
    lines.append(_card_line(f"Total systems: {total}", CARD_WIDTH))
    lines.append(
        _card_line(
            f"SSH reachable: {reachable} | Not reachable: {unreachable}",
            CARD_WIDTH,
        )
    )
    lines.append(_card_line(f"Runtime: {timestamp}", CARD_WIDTH))
    lines.append("╚" + "═" * (CARD_WIDTH - 2) + "╝")
    lines.append("")

    table_lines = build_pdf_table(hosts)
    if table_lines:
        lines.extend(table_lines)
    else:
        lines.append("No systems present in the report.")

    return lines


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def split_into_pages(lines: Sequence[str]) -> List[List[str]]:
    lines_per_page = max(1, int((PAGE_HEIGHT - 2 * MARGIN) / LINE_HEIGHT))
    pages: List[List[str]] = []
    for start in range(0, len(lines), lines_per_page):
        pages.append(list(lines[start:start + lines_per_page]))
    return pages or [[]]


def new_object(objects: List[str | None], body: str | None = None) -> int:
    objects.append(body)
    return len(objects)


def set_object(objects: List[str | None], obj_id: int, body: str) -> None:
    objects[obj_id - 1] = body


def create_pdf(lines: Sequence[str], output_path: str) -> None:
    pages = split_into_pages(lines)
    objects: List[str | None] = []

    catalog_obj = new_object(objects, None)
    pages_obj = new_object(objects, None)
    font_obj = new_object(objects, "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    page_ids: List[int] = []
    for page_lines in pages:
        text_elements = [
            "BT",
            f"/F1 {FONT_SIZE} Tf",
            f"{LINE_HEIGHT} TL",
            f"1 0 0 1 {MARGIN} {PAGE_HEIGHT - MARGIN - FONT_SIZE} Tm",
        ]
        for index, line in enumerate(page_lines):
            content = escape_pdf_text(line)
            if index == 0:
                text_elements.append(f"({content}) Tj")
            else:
                text_elements.append("T*")
                text_elements.append(f"({content}) Tj")
        text_elements.append("ET")
        stream_data = "\n".join(text_elements)
        encoded = stream_data.encode("utf-8")
        stream_obj = new_object(
            objects,
            f"<< /Length {len(encoded)} >>\nstream\n{stream_data}\nendstream",
        )
        page_obj = new_object(objects, None)
        page_body = (
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {stream_obj} 0 R /Resources << /Font << /F1 {font_obj} 0 R >> >> >>"
        )
        set_object(objects, page_obj, page_body)
        page_ids.append(page_obj)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids) or ""
    set_object(objects, pages_obj, f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
    set_object(objects, catalog_obj, f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

    with open(output_path, "wb") as handle:
        handle.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets: List[int] = []
        for index, body in enumerate(objects, start=1):
            if body is None:
                raise ValueError(f"PDF object {index} is undefined")
            offsets.append(handle.tell())
            handle.write(f"{index} 0 obj\n{body}\nendobj\n".encode("utf-8"))
        xref_start = handle.tell()
        handle.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        handle.write(b"0000000000 65535 f \n")
        for offset in offsets:
            handle.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        trailer = (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        )
        handle.write(trailer.encode("ascii"))


def render_pdf_via_browser(html_path: Path, pdf_path: Path) -> bool:
    browsers = [
        "chromium-browser",
        "chromium",
        "google-chrome",
        "google-chrome-stable",
        "chrome",
        "msedge",
        "microsoft-edge",
        "brave-browser",
    ]

    html_uri = html_path.resolve().as_uri()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    for name in browsers:
        browser = shutil.which(name)
        if not browser:
            continue
        for headless_arg in ("--headless=new", "--headless"):
            command = [
                browser,
                headless_arg,
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={pdf_path}",
                "--print-to-pdf-no-header",
                html_uri,
            ]
            try:
                subprocess.run(
                    command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            if pdf_path.exists():
                return True
            break
    return False


def load_icon_data_uri() -> Optional[str]:
    icon_candidates = [
        Path(__file__).with_name("risng_icon_increment.png"),
        Path(__file__).with_name("risng_icon.png"),
    ]

    for icon_path in icon_candidates:
        if icon_path.exists():
            encoded = base64.b64encode(icon_path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    return None


def load_banner_data_uri() -> Optional[str]:
    banner_candidates = [
        Path(__file__).with_name("banner-rechteck.png"),
    ]

    for banner_path in banner_candidates:
        if banner_path.exists():
            encoded = base64.b64encode(banner_path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
    return None


def render_html(
    hosts: Sequence[dict],
    metadata: dict,
    output_path: Path,
    icon_data_uri: Optional[str],
    banner_data_uri: Optional[str],
) -> None:
    total = metadata.get("total", len(hosts))
    reachable = metadata.get("reachable", 0)
    unreachable = metadata.get("unreachable", max(0, total - reachable))
    timestamp = metadata.get("timestamp", "-")
    timestamp_iso = metadata.get("timestamp_iso", timestamp)
    title = metadata.get("title", "RISng Client Report")
    subtitle = metadata.get(
        "subtitle", "The listed clients were intended to be tested through RISng."
    )

    rows: List[str] = []
    for host in hosts:
        host_name = html.escape(host["host"])
        assigned_name = html.escape(host.get("assigned", ""))
        mac_addr = html.escape(host["mac"])
        raw_pingpartners = host.get("pingpartners") or []
        ping_statuses = host.get("pingpartner_status") or {}
        ping_partner_tags: List[str] = []
        if raw_pingpartners:
            for partner in raw_pingpartners:
                label = html.escape(partner or "n/a") or "n/a"
                status = str(ping_statuses.get(partner, "")).lower()
                badge_classes = ["badge", "badge--pingpartner"]
                if status == "success":
                    badge_classes.append("badge--ok")
                else:
                    badge_classes.append("badge--warn")
                aria_label = f"pingpartner {label}"
                if status:
                    aria_label += f" status {status}"
                badge_class = " ".join(badge_classes)
                ping_partner_tags.append(
                    f"<span class='{badge_class}' aria-label='{html.escape(aria_label)}'>"
                    f"{label}</span>"
                )
        else:
            ping_partner_tags.append(
                "<span class='badge badge--warn badge--pingpartner'>n/a</span>"
            )
        ping_partner = "<div class='pingpartner-list'>" + "".join(ping_partner_tags) + "</div>"
        success_times = host.get("pingpartner_success_list") or []
        if success_times:
            success_badges = "".join(
                f"<span class='badge badge--time'>{html.escape(item)}</span>"
                for item in success_times
            )
            ping_success_block = (
                f"<div class='pingpartner-success-list'>{success_badges}</div>"
            )
        else:
            ping_success_block = (
                "<span class='empty'>No successful pingpartner test</span>"
            )
        volume = html.escape(host.get("system_volume", "n/a"))
        is_reachable = bool(host.get("reachable_flag"))
        reachable_badge = (
            '<span class="badge badge--ok">Yes</span>'
            if is_reachable
            else '<span class="badge badge--warn">No</span>'
        )
        interfaces = host.get("interfaces") or []
        if interfaces:
            interface_html = "".join(
                f"<li>{linkify_ips(item)}</li>" for item in interfaces
            )
            interface_block = f"<ul class='interface-list'>{interface_html}</ul>"
        else:
            interface_block = "<span class='empty'>No network adapters captured</span>"

        row_class = " row--reachable" if is_reachable else " row--unreachable"
        rows.append(
            "<tr class='report-row" + row_class + "'>"
            f"<td data-label='Hostname'><span class='host-name'>{host_name}</span></td>"
            f"<td data-label='hostname assigned'>{assigned_name}</td>"
            f"<td data-label='PXE-Mac Address'>{mac_addr}</td>"
            f"<td data-label='SSH Reachable'>{reachable_badge}</td>"
            f"<td data-label='System Volume'>{volume}</td>"
            f"<td data-label='Network Adapters'>{interface_block}</td>"
            f"<td data-label='pingpartner'>{ping_partner}</td>"
            f"<td data-label='pingpartner success'>{ping_success_block}</td>"
            "</tr>"
        )

    table_content = "\n".join(rows)
    if rows:
        table_section = (
            "<table class='report-table'>"
            "<colgroup>"
            "<col class='col-hostname' />"
            "<col class='col-assigned' />"
            "<col class='col-pxe' />"
            "<col class='col-reachable' />"
            "<col class='col-volume' />"
            "<col class='col-network' />"
            "<col class='col-ping' />"
            "<col class='col-ping-success' />"
            "</colgroup>"
            "<thead>"
            "<tr>"
            "<th scope='col'>Hostname</th>"
            "<th scope='col'>hostname assigned</th>"
            "<th scope='col'>PXE-Mac Address</th>"
            "<th scope='col'>SSH Reachable</th>"
            "<th scope='col'>System Volume</th>"
            "<th scope='col'>Network Adapters</th>"
            "<th scope='col'>pingpartner</th>"
            "<th scope='col'>pingpartner success</th>"
            "</tr>"
            "</thead>"
            f"<tbody>{table_content}</tbody>"
            "</table>"
        )
    else:
        table_section = (
            "<div class='empty-state'>"
            "<h2>No systems in the report</h2>"
            "<p>Run proxreport to collect up-to-date information.</p>"
            "</div>"
        )

    if icon_data_uri:
        icon_markup = (
            f"<img src='{icon_data_uri}' alt='RISng logo' width='64' height='64' />"
        )
    else:
        icon_markup = "<span class='report-initials' aria-hidden='true'>IS</span>"

    if banner_data_uri:
        banner_markup = (
            "<div class='report-banner' role='img' aria-label='RISng banner'>"
            f"<img src='{banner_data_uri}' alt='RISng banner' />"
            "</div>"
        )
    else:
        banner_markup = ""

    html_output = f"""<!DOCTYPE html>
<html lang='en'>
  <head>
    <meta charset='UTF-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1' />
    <title>{html.escape(title)}</title>
    <style>
      @page {{
        size: A4 landscape;
        margin: 1.5cm;
      }}

      :root {{
        color-scheme: light dark;
        --bg-light: #f2f5f9;
        --bg-dark: #1f2933;
        --card-light: #ffffff;
        --card-dark: #273241;
        --accent: #1d72b8;
        --accent-soft: rgba(29, 114, 184, 0.15);
        --text-light: #243447;
        --text-dark: #e6edf3;
        --muted-light: rgba(36, 52, 71, 0.65);
        --muted-dark: rgba(230, 237, 243, 0.62);
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 3rem 1.5rem;
        font-family: "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 12px;
        background: linear-gradient(135deg, rgba(29, 114, 184, 0.18), rgba(29, 114, 184, 0.05)),
          var(--bg-light);
        color: var(--text-light);
      }}

      @media (prefers-color-scheme: dark) {{
        body {{
          background: linear-gradient(135deg, rgba(29, 114, 184, 0.28), rgba(13, 60, 110, 0.25)),
            var(--bg-dark);
          color: var(--text-dark);
        }}
      }}

      main {{
        width: 100%;
      }}

      .report-card {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 2.5rem 2.75rem;
        border-radius: 24px;
        background: var(--card-light);
        box-shadow: 0 24px 55px rgba(15, 23, 42, 0.18);
        position: relative;
        overflow: hidden;
      }}

      @media (prefers-color-scheme: dark) {{
        .report-card {{
          background: var(--card-dark);
          box-shadow: 0 24px 55px rgba(0, 0, 0, 0.48);
        }}
      }}

      .report-card::before {{
        content: "";
        position: absolute;
        inset: -45% auto auto -25%;
        width: 520px;
        height: 520px;
        background: radial-gradient(circle at center, rgba(29, 114, 184, 0.23), transparent 68%);
        z-index: 0;
      }}

      .report-card > * {{
        position: relative;
        z-index: 1;
      }}

      .report-header {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1.6rem;
        justify-content: space-between;
      }}

      .report-banner {{
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 88px;
        padding: 14px 18px;
        border-radius: 22px;
        background: rgba(29, 114, 184, 0.12);
        box-shadow: inset 0 0 0 2px rgba(29, 114, 184, 0.18);
        max-width: 320px;
      }}

      .report-brand {{
        display: flex;
        align-items: center;
        gap: 1.6rem;
        flex: 1 1 auto;
        min-width: 320px;
      }}

      .report-icon {{
        width: 88px;
        height: 88px;
        border-radius: 22px;
        background: rgba(29, 114, 184, 0.12);
        display: grid;
        place-items: center;
        color: #1d72b8;
        box-shadow: inset 0 0 0 2px rgba(29, 114, 184, 0.18);
        overflow: hidden;
      }}

      .report-icon img {{
        width: 64px;
        height: 64px;
        object-fit: contain;
      }}

      .report-initials {{
        font-size: 1.75rem;
        font-weight: 600;
      }}

      .report-title {{
        flex: 1 1 320px;
      }}

      .report-title h1 {{
        margin: 0;
        font-size: 1.9rem;
        font-weight: 600;
      }}

      .report-title p {{
        margin: 0.4rem 0 0;
        font-size: 1.05rem;
        color: var(--muted-light);
      }}

      @media (prefers-color-scheme: dark) {{
        .report-title p {{
          color: var(--muted-dark);
        }}
      }}

      .report-banner img {{
        display: block;
        max-width: 100%;
        height: 64px;
        object-fit: contain;
      }}

      .report-meta {{
        margin-top: 2.4rem;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.25rem;
      }}

      .meta-item {{
        padding: 1rem 1.25rem;
        border-radius: 18px;
        background: rgba(29, 114, 184, 0.08);
        color: inherit;
      }}

      .meta-item span {{
        display: block;
        font-size: 0.82rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted-light);
        margin-bottom: 0.5rem;
      }}

      .meta-item strong {{
        font-size: 1.45rem;
      }}

      @media (prefers-color-scheme: dark) {{
        .meta-item {{
          background: rgba(29, 114, 184, 0.16);
        }}

        .meta-item span {{
          color: var(--muted-dark);
        }}
      }}

      .report-table {{
        width: 100%;
        margin-top: 2.4rem;
        border-collapse: collapse;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        overflow: hidden;
        table-layout: fixed;
        font-size: 0.88rem;
      }}

      thead {{
        background: rgba(29, 114, 184, 0.12);
      }}

      th,
      td {{
        padding: 0.85rem 1rem;
        text-align: left;
        vertical-align: top;
        word-break: break-word;
      }}

      .report-table col.col-hostname {{
        width: 12%;
      }}

      .report-table col.col-assigned {{
        width: 13%;
      }}

      .report-table col.col-pxe {{
        width: 11%;
      }}

      .report-table col.col-reachable {{
        width: 7%;
      }}

      .report-table col.col-volume {{
        width: 12%;
      }}

      .report-table col.col-network {{
        width: 27%;
      }}

      .report-table col.col-ping {{
        width: 9%;
      }}

      .report-table col.col-ping-success {{
        width: 9%;
      }}

      tbody tr {{
        border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        transition: background 0.2s ease;
      }}

      tbody tr:last-child {{
        border-bottom: none;
      }}

      tbody tr:hover {{
        background: rgba(29, 114, 184, 0.08);
      }}

      .row--unreachable {{
        opacity: 0.82;
      }}

      .host-name {{
        font-weight: 600;
        font-size: 0.95rem;
      }}

      .badge {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.3rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.03em;
      }}

      .badge--ok {{
        color: #0f5132;
        background: rgba(25, 135, 84, 0.2);
      }}

      .badge--warn {{
        color: #842029;
        background: rgba(220, 53, 69, 0.18);
      }}

      .pingpartner-list {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
      }}

      .pingpartner-success-list {{
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
      }}

      .badge--pingpartner {{
        min-width: 3rem;
        justify-content: center;
        font-size: calc(0.82rem - 3pt);
      }}

      .badge--time {{
        background: rgba(13, 110, 253, 0.15);
        color: #0c5394;
        justify-content: flex-start;
        font-weight: 600;
      }}

      .interface-list {{
        margin: 0;
        padding-left: 1.1rem;
        list-style: disc;
      }}

      .interface-list li {{
        margin: 0.2rem 0;
      }}

      .ip-link {{
        color: #1d72b8;
        font-weight: 600;
        text-decoration: none;
      }}

      .ip-link:hover,
      .ip-link:focus {{
        text-decoration: underline;
      }}

      .empty {{
        color: var(--muted-light);
        font-style: italic;
      }}

      @media (prefers-color-scheme: dark) {{
        .empty {{
          color: var(--muted-dark);
        }}

        tbody tr {{
          border-bottom: 1px solid rgba(148, 163, 184, 0.12);
        }}

        tbody tr:hover {{
          background: rgba(29, 114, 184, 0.18);
        }}

        .ip-link {{
          color: #8cbcff;
        }}
      }}

      @media print {{
        body {{
          background: #ffffff !important;
          color: #1f2933;
          display: block;
          padding: 0;
        }}

        main {{
          width: auto;
        }}

        .report-card {{
          max-width: none;
          margin: 0;
          padding: 1.3cm 1.5cm;
          border-radius: 0;
          box-shadow: none;
          background: transparent;
        }}

        .report-header {{
          align-items: flex-start;
        }}

        .report-title h1 {{
          font-size: 1.5rem;
        }}

        .report-title p {{
          font-size: 0.9rem;
        }}

        .report-meta {{
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
        }}

        .meta-item {{
          background: rgba(29, 114, 184, 0.12);
          padding: 0.75rem 1rem;
        }}

        table {{
          margin-top: 1.5rem;
          font-size: 0.8rem;
        }}

        th,
        td {{
          padding: 0.5rem 0.6rem;
        }}

        .host-name {{
          font-size: 0.9rem;
        }}

        .badge {{
          font-size: 0.75rem;
          padding: 0.22rem 0.52rem;
        }}

        .interface-list {{
          padding-left: 1rem;
        }}

        .interface-list li {{
          margin: 0.1rem 0;
        }}

        .report-footer {{
          margin-top: 1.5rem;
          font-size: 0.82rem;
        }}
      }}

      .empty-state {{
        margin-top: 3rem;
        text-align: center;
        padding: 3rem 1.5rem;
        border-radius: 18px;
        background: rgba(29, 114, 184, 0.1);
      }}

      .empty-state h2 {{
        margin: 0;
        font-size: 1.6rem;
      }}

      .empty-state p {{
        margin: 0.75rem 0 0;
        color: var(--muted-light);
      }}

      @media (max-width: 720px) {{
        .report-card {{
          padding: 2rem 1.5rem;
        }}

        thead {{
          display: none;
        }}

        table,
        tbody,
        tr,
        td {{
          display: block;
          width: 100%;
        }}

        tbody tr {{
          padding: 1.25rem 0;
          border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        }}

        td {{
          padding: 0.4rem 0;
        }}

        td::before {{
          content: attr(data-label);
          display: block;
          font-size: 0.78rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--accent);
          margin-bottom: 0.45rem;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <article class='report-card'>
        <header class='report-header'>
          <div class='report-brand'>
            <div class='report-icon' aria-hidden='true'>{icon_markup}</div>
            <div class='report-title'>
              <h1>{html.escape(title)}</h1>
              <p>{html.escape(subtitle)}</p>
            </div>
          </div>
          {banner_markup}
        </header>

        <section class='report-meta'>
          <div class='meta-item'>
            <span>Total systems</span>
            <strong>{total}</strong>
          </div>
          <div class='meta-item'>
            <span>SSH reachable</span>
            <strong>{reachable}</strong>
          </div>
          <div class='meta-item'>
            <span>Not reachable</span>
            <strong>{unreachable}</strong>
          </div>
          <div class='meta-item'>
            <span>Runtime</span>
            <strong><time datetime='{timestamp_iso}'>{html.escape(timestamp)}</time></strong>
          </div>
        </section>

        {table_section}

      </article>
    </main>
  </body>
</html>
"""

    output_path.write_text(html_output, encoding="utf-8")


def main(argv: Sequence[str]) -> int:
    if len(argv) != 3:
        usage()
        return 1

    input_path = argv[1]
    output_path = argv[2]

    entries = load_report(input_path)
    pingpartner_results = load_pingpartner_results()
    hosts = build_host_data(entries, pingpartner_results)
    generated_at = datetime.now()
    metadata = build_metadata(hosts, generated_at)

    pdf_path = Path(output_path)
    if pdf_path.suffix:
        html_path = pdf_path.with_suffix(".html")
    else:
        html_path = pdf_path.with_name(pdf_path.name + ".html")
    icon_data_uri = load_icon_data_uri()
    banner_data_uri = load_banner_data_uri()
    render_html(hosts, metadata, html_path, icon_data_uri, banner_data_uri)

    if not render_pdf_via_browser(html_path, pdf_path):
        lines = build_pdf_lines(hosts, metadata)
        create_pdf(lines, str(pdf_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
