#!/usr/bin/env python3
"""Render NetBox VLAN data from JSON into HTML and PDF summaries."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYTHONPYCACHEPREFIX", str(Path.home() / ".cache" / "pycache"))

import base64
import html
import json
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from typing import Iterable, List, MutableSequence, Optional, Sequence

PAGE_WIDTH = 842  # A4 landscape width in points
PAGE_HEIGHT = 595
MARGIN = 36
FONT_SIZE = 10
LINE_HEIGHT = 14

TABLE_COLUMNS = [
    ("VLAN", 28),
    ("VID", 8),
    ("Site", 18),
    ("Group", 18),
    ("Role", 16),
    ("Status", 12),
    ("Tenant", 18),
    ("Tags", 32),
]

TABLE_DIVIDER = "+" + "+".join("-" * (width + 2) for _, width in TABLE_COLUMNS) + "+"
TABLE_HEADER_DIVIDER = "+" + "+".join("=" * (width + 2) for _, width in TABLE_COLUMNS) + "+"
CARD_WIDTH = len(TABLE_DIVIDER)


def usage() -> None:
    print(
        "Usage: netbox_vlan_report.py <input.json> <output.pdf>",
        "\n\nThe script also creates a matching HTML report next to the PDF output.",
        sep="",
        file=sys.stderr,
    )


def load_payload(path: Path) -> tuple[dict, List[dict]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise SystemExit(f"Input JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Input JSON is invalid: {exc}") from exc

    if isinstance(data, list):
        return {}, list(data)

    if not isinstance(data, dict):
        raise SystemExit("Input JSON must contain either a list or an object with 'vlans'.")

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    vlans = data.get("vlans")
    if not isinstance(vlans, list):
        vlans = []

    return metadata, vlans


def _text(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        result = value.strip()
        return result if result else default
    return str(value)


def _collect_tags(raw: Iterable[object]) -> List[str]:
    tags: List[str] = []
    for item in raw:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                tags.append(cleaned)
            continue
        if isinstance(item, dict):
            for key in ("name", "label", "slug"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    tags.append(value.strip())
                    break
    seen: set[str] = set()
    deduped: List[str] = []
    for tag in tags:
        lower = tag.lower()
        if lower in seen:
            continue
        seen.add(lower)
        deduped.append(tag)
    return deduped


def build_vlan_entries(raw_vlans: Sequence[dict]) -> List[dict]:
    entries: List[dict] = []
    for vlan in raw_vlans:
        if not isinstance(vlan, dict):
            continue
        name = _text(vlan.get("name"), default="<unnamed>")
        vid = _text(vlan.get("vid"))
        site = _text(_extract_name(vlan.get("site")))
        group = _text(_extract_name(vlan.get("group")))
        role = _text(_extract_name(vlan.get("role")))
        tenant = _text(_extract_name(vlan.get("tenant")))
        status = _status_label(vlan.get("status"))
        description = _text(vlan.get("description"))
        tags = _collect_tags(vlan.get("tags") or [])

        entries.append(
            {
                "name": name,
                "vid": vid,
                "site": site or "n/a",
                "group": group or "n/a",
                "role": role or "n/a",
                "status": status or "n/a",
                "tenant": tenant or "n/a",
                "description": description,
                "tags": tags,
            }
        )

    entries.sort(
        key=lambda item: (
            item["site"].lower(),
            item["group"].lower(),
            item["vid"].zfill(4),
            item["name"].lower(),
        )
    )
    return entries


def _extract_name(value: object) -> str:
    if isinstance(value, dict):
        for key in ("name", "label", "value"):
            potential = value.get(key)
            if isinstance(potential, str) and potential.strip():
                return potential.strip()
    return _text(value)


def _status_label(value: object) -> str:
    if isinstance(value, dict):
        for key in ("label", "value", "name"):
            potential = value.get(key)
            if isinstance(potential, str) and potential.strip():
                return potential.strip()
    return _text(value)


def parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.utcnow()
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return datetime.utcnow()


def build_metadata(raw_meta: dict, vlans: Sequence[dict]) -> dict:
    generated_at = parse_timestamp(_text(raw_meta.get("generated_at"), default=""))
    username = _text(raw_meta.get("username"), default="unknown user")
    base_url = _text(raw_meta.get("base_url"))
    vlan_count = raw_meta.get("vlan_count")
    try:
        total = int(vlan_count)
    except (TypeError, ValueError):
        total = len(vlans)

    title = _text(raw_meta.get("title"), default="NetBox VLAN Search")
    subtitle = _text(
        raw_meta.get("subtitle"),
        default=f"VLAN overview for {username}",
    )

    return {
        "title": title,
        "subtitle": subtitle,
        "generated_at": generated_at,
        "timestamp": generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_iso": generated_at.isoformat(timespec="seconds"),
        "username": username,
        "base_url": base_url,
        "total": total,
    }


def _wrap_cell(content: str, width: int) -> List[str]:
    wrapper = textwrap.TextWrapper(
        width=width,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=False,
    )
    lines = wrapper.wrap(content.strip())
    return lines or [""]


def _wrap_tags(tags: Sequence[str], width: int) -> List[str]:
    if not tags:
        return ["—"]
    return _wrap_cell(", ".join(tags), width)


def _format_table_line(values: Sequence[str]) -> str:
    padded = [
        f" {value.ljust(width)} "
        for (value, (_, width)) in zip(values, TABLE_COLUMNS)
    ]
    return "|" + "|".join(padded) + "|"


def build_pdf_table(vlans: Sequence[dict]) -> List[str]:
    lines: List[str] = [TABLE_DIVIDER]
    header = [name.upper() for name, _ in TABLE_COLUMNS]
    lines.append(_format_table_line(header))
    lines.append(TABLE_HEADER_DIVIDER)

    for vlan in vlans:
        vlan_name_lines = _wrap_cell(vlan["name"], TABLE_COLUMNS[0][1])
        if vlan["description"]:
            description_lines = _wrap_cell(vlan["description"], TABLE_COLUMNS[0][1])
            vlan_name_lines = vlan_name_lines + [""] + description_lines
        vid_lines = _wrap_cell(vlan["vid"] or "—", TABLE_COLUMNS[1][1])
        site_lines = _wrap_cell(vlan["site"], TABLE_COLUMNS[2][1])
        group_lines = _wrap_cell(vlan["group"], TABLE_COLUMNS[3][1])
        role_lines = _wrap_cell(vlan["role"], TABLE_COLUMNS[4][1])
        status_lines = _wrap_cell(vlan["status"], TABLE_COLUMNS[5][1])
        tenant_lines = _wrap_cell(vlan["tenant"], TABLE_COLUMNS[6][1])
        tags_lines = _wrap_tags(vlan["tags"], TABLE_COLUMNS[7][1])

        max_lines = max(
            len(vlan_name_lines),
            len(vid_lines),
            len(site_lines),
            len(group_lines),
            len(role_lines),
            len(status_lines),
            len(tenant_lines),
            len(tags_lines),
        )

        for index in range(max_lines):
            row = [
                vlan_name_lines[index] if index < len(vlan_name_lines) else "",
                vid_lines[index] if index < len(vid_lines) else "",
                site_lines[index] if index < len(site_lines) else "",
                group_lines[index] if index < len(group_lines) else "",
                role_lines[index] if index < len(role_lines) else "",
                status_lines[index] if index < len(status_lines) else "",
                tenant_lines[index] if index < len(tenant_lines) else "",
                tags_lines[index] if index < len(tags_lines) else "",
            ]
            lines.append(_format_table_line(row))
        lines.append(TABLE_DIVIDER)

    return lines


def _card_line(text: str, width: int, *, align: str = "left") -> str:
    inner = max(0, width - 4)
    if align == "center":
        content = text.center(inner)
    else:
        content = text.ljust(inner)
    return f"║ {content} ║"


def build_pdf_lines(vlans: Sequence[dict], metadata: dict) -> List[str]:
    lines: List[str] = []
    title = metadata.get("title", "NetBox VLAN Search")
    subtitle = metadata.get("subtitle", "")
    total = metadata.get("total", len(vlans))
    timestamp = metadata.get("timestamp", "")
    base_url = metadata.get("base_url")

    lines.append("╔" + "═" * (CARD_WIDTH - 2) + "╗")
    lines.append(_card_line(title, CARD_WIDTH, align="center"))
    if subtitle:
        lines.append(_card_line(subtitle, CARD_WIDTH, align="center"))
    lines.append("╠" + "═" * (CARD_WIDTH - 2) + "╣")
    lines.append(_card_line(f"Total VLANs: {total}", CARD_WIDTH))
    if timestamp:
        lines.append(_card_line(f"Generated: {timestamp}", CARD_WIDTH))
    if base_url:
        lines.append(_card_line(f"Source: {base_url}", CARD_WIDTH))
    lines.append("╚" + "═" * (CARD_WIDTH - 2) + "╝")
    lines.append("")

    table_lines = build_pdf_table(vlans)
    if table_lines:
        lines.extend(table_lines)
    else:
        lines.append("No VLAN entries present in the report.")

    return lines


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def split_into_pages(lines: Sequence[str]) -> List[List[str]]:
    lines_per_page = max(1, int((PAGE_HEIGHT - 2 * MARGIN) / LINE_HEIGHT))
    pages: List[List[str]] = []
    for start in range(0, len(lines), lines_per_page):
        pages.append(list(lines[start:start + lines_per_page]))
    return pages or [[]]


def new_object(objects: MutableSequence[str | None], body: str | None = None) -> int:
    objects.append(body)
    return len(objects)


def set_object(objects: MutableSequence[str | None], obj_id: int, body: str) -> None:
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
        stream_obj = new_object(
            objects,
            f"<< /Length {len(stream_data.encode('utf-8'))} >>\nstream\n{stream_data}\nendstream",
        )
        page_obj = new_object(
            objects,
            f"<< /Type /Page /Parent {pages_obj} 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {stream_obj} 0 R "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> >>",
        )
        page_ids.append(page_obj)

    set_object(
        objects,
        pages_obj,
        "<< /Type /Pages /Kids [" + " ".join(f"{pid} 0 R" for pid in page_ids) + f"] /Count {len(page_ids)} >>",
    )
    set_object(objects, catalog_obj, f"<< /Type /Catalog /Pages {pages_obj} 0 R >>")

    xref_positions: List[int] = []
    with open(output_path, "wb") as handle:
        handle.write(b"%PDF-1.4\n")
        for index, body in enumerate(objects, start=1):
            xref_positions.append(handle.tell())
            if body is None:
                body = ""
            handle.write(f"{index} 0 obj\n{body}\nendobj\n".encode("utf-8"))
        xref_start = handle.tell()
        handle.write(b"xref\n")
        handle.write(f"0 {len(objects) + 1}\n".encode("utf-8"))
        handle.write(b"0000000000 65535 f \n")
        for pos in xref_positions:
            handle.write(f"{pos:010d} 00000 n \n".encode("utf-8"))
        handle.write(b"trailer\n")
        handle.write(
            f"<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode(
                "utf-8"
            )
        )


def load_icon_data_uri() -> Optional[str]:
    icon_candidates = [
        Path(__file__).resolve().parents[2]
        / "runtime"
        / "report_snapshot"
        / "files"
        / "risng_icon.png",
        Path(__file__).resolve().parents[2]
        / "runtime"
        / "report_increment"
        / "files"
        / "risng_icon.png",
    ]

    for icon_path in icon_candidates:
        if icon_path.exists():
            encoded = base64.b64encode(icon_path.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{encoded}"

    return None


def render_pdf_via_browser(html_path: Path, pdf_path: Path) -> bool:
    browsers = [
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
        "chromium-freeworld",
        "google-chrome-beta",
    ]

    html_uri = html_path.resolve().as_uri()
    pdf_path = pdf_path.resolve()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    for browser in browsers:
        if shutil.which(browser) is None:
            continue
        command = [
            browser,
            "--headless",
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
    return False


def render_html(vlans: Sequence[dict], metadata: dict, output_path: Path, icon_data_uri: Optional[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[str] = []
    for vlan in vlans:
        tags = vlan.get("tags") or []
        if tags:
            tag_html = "".join(f"<span class='tag'>{html.escape(tag)}</span>" for tag in tags)
        else:
            tag_html = "<span class='tag tag--empty'>No tags</span>"

        description = vlan.get("description")
        if description:
            description_html = f"<p class='vlan-description'>{html.escape(description)}</p>"
        else:
            description_html = ""

        rows.append(
            "<tr>",
            f"<td data-label='VLAN'><span class='vlan-name'>{html.escape(vlan['name'])}</span>{description_html}</td>",
            f"<td data-label='VID'>{html.escape(vlan['vid'] or '—')}</td>",
            f"<td data-label='Site'>{html.escape(vlan['site'])}</td>",
            f"<td data-label='Group'>{html.escape(vlan['group'])}</td>",
            f"<td data-label='Role'>{html.escape(vlan['role'])}</td>",
            f"<td data-label='Status'>{html.escape(vlan['status'])}</td>",
            f"<td data-label='Tenant'>{html.escape(vlan['tenant'])}</td>",
            f"<td data-label='Tags'>{tag_html}</td>",
            "</tr>",
        )

    if rows:
        table_section = (
            "<table>"
            "<thead>"
            "<tr>"
            + "".join(f"<th scope='col'>{html.escape(col)}</th>" for col, _ in TABLE_COLUMNS)
            + "</tr>"
            "</thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )
    else:
        table_section = (
            "<div class='empty-state'>"
            "<h2>No VLANs returned from NetBox</h2>"
            "<p>Adjust the filter template to populate this report.</p>"
            "</div>"
        )

    if icon_data_uri:
        icon_markup = (
            f"<img src='{icon_data_uri}' alt='RISng logo' "
            "width='64' height='64' class='report-icon' />"
        )
    else:
        icon_markup = "<span class='report-initials' aria-hidden='true'>IS</span>"

    title = html.escape(metadata.get("title", "NetBox VLAN Search"))
    subtitle = html.escape(metadata.get("subtitle", ""))
    total = metadata.get("total", len(vlans))
    timestamp = html.escape(metadata.get("timestamp", ""))
    base_url = metadata.get("base_url")
    base_url_html = (
        f"<p class='meta-line'><strong>Source:</strong> {html.escape(base_url)}</p>" if base_url else ""
    )

    html_output = f"""<!DOCTYPE html>
<html lang='en'>
  <head>
    <meta charset='UTF-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1' />
    <title>{title}</title>
    <style>
      @page {{
        size: A4 landscape;
        margin: 1.5cm;
      }}

      :root {{
        color-scheme: light dark;
        --bg-light: #f5f7fb;
        --bg-dark: #111827;
        --card-light: rgba(255, 255, 255, 0.75);
        --card-dark: rgba(15, 23, 42, 0.9);
        --text-light: #0f172a;
        --text-dark: #e2e8f0;
        --accent: #2563eb;
      }}

      body {{
        margin: 0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(120deg, var(--bg-light), rgba(148, 163, 184, 0.2));
        color: var(--text-light);
        padding: 2rem;
      }}

      @media (prefers-color-scheme: dark) {{
        body {{
          background: linear-gradient(120deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.6));
          color: var(--text-dark);
        }}
      }}

      .report {{
        max-width: 1200px;
        margin: 0 auto;
        background: var(--card-light);
        border-radius: 18px;
        padding: 2.5rem;
        box-shadow: 0 24px 48px rgba(15, 23, 42, 0.18);
        backdrop-filter: blur(24px);
      }}

      @media (prefers-color-scheme: dark) {{
        .report {{
          background: var(--card-dark);
          box-shadow: 0 24px 48px rgba(2, 6, 23, 0.65);
        }}
      }}

      .report-header {{
        display: flex;
        align-items: center;
        gap: 1.75rem;
        margin-bottom: 1.5rem;
      }}

      .report-header .report-icon,
      .report-header .report-initials {{
        width: 72px;
        height: 72px;
        border-radius: 18px;
        background: rgba(37, 99, 235, 0.12);
        display: grid;
        place-items: center;
        font-weight: 700;
        font-size: 1.75rem;
        color: var(--accent);
      }}

      .report-header h1 {{
        margin: 0;
        font-size: 2rem;
      }}

      .report-subtitle {{
        margin: 0.25rem 0 0;
        color: rgba(71, 85, 105, 0.8);
      }}

      .report-meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        margin-bottom: 2rem;
      }}

      .meta-line {{
        margin: 0;
        font-weight: 500;
        color: rgba(15, 23, 42, 0.8);
      }}

      @media (prefers-color-scheme: dark) {{
        .meta-line {{
          color: rgba(226, 232, 240, 0.85);
        }}
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
        background: rgba(255, 255, 255, 0.6);
        border-radius: 16px;
        overflow: hidden;
      }}

      @media (prefers-color-scheme: dark) {{
        table {{
          background: rgba(15, 23, 42, 0.85);
        }}
      }}

      th {{
        text-align: left;
        padding: 0.9rem 1rem;
        background: rgba(37, 99, 235, 0.08);
        font-size: 0.85rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }}

      td {{
        padding: 0.9rem 1rem;
        border-top: 1px solid rgba(148, 163, 184, 0.2);
        vertical-align: top;
      }}

      .vlan-name {{
        font-weight: 600;
        font-size: 1rem;
      }}

      .vlan-description {{
        margin: 0.35rem 0 0;
        font-size: 0.9rem;
        color: rgba(71, 85, 105, 0.85);
      }}

      .tag {{
        display: inline-flex;
        align-items: center;
        margin: 0.1rem;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        background: rgba(37, 99, 235, 0.12);
        color: #1d4ed8;
        font-size: 0.8rem;
        font-weight: 600;
      }}

      .tag--empty {{
        background: rgba(239, 68, 68, 0.15);
        color: #b91c1c;
        font-weight: 500;
      }}

      .empty-state {{
        text-align: center;
        padding: 4rem 2rem;
        border-radius: 16px;
        background: rgba(148, 163, 184, 0.12);
        color: rgba(71, 85, 105, 0.85);
      }}

      @media (prefers-color-scheme: dark) {{
        .empty-state {{
          background: rgba(30, 41, 59, 0.6);
          color: rgba(226, 232, 240, 0.75);
        }}
      }}

      @media (max-width: 960px) {{
        table, thead, tbody, th, td, tr {{
          display: block;
        }}

        thead {{
          display: none;
        }}

        tr {{
          margin-bottom: 1rem;
          border: 1px solid rgba(148, 163, 184, 0.25);
          border-radius: 12px;
          overflow: hidden;
        }}

        td {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.75rem;
          border-bottom: 1px solid rgba(148, 163, 184, 0.15);
        }}

        td::before {{
          content: attr(data-label);
          font-weight: 600;
          margin-right: 0.75rem;
        }}

        td:last-child {{
          border-bottom: none;
        }}
      }}
    </style>
  </head>
  <body>
    <main class='report'>
      <header class='report-header'>
        {icon_markup}
        <div>
          <h1>{title}</h1>
          <p class='report-subtitle'>{subtitle}</p>
        </div>
      </header>
      <section class='report-meta'>
        <p class='meta-line'><strong>Total VLANs:</strong> {total}</p>
        <p class='meta-line'><strong>Generated:</strong> {timestamp}</p>
        {base_url_html}
      </section>
      {table_section}
    </main>
  </body>
</html>
"""

    output_path.write_text(html_output, encoding="utf-8")


def main(argv: Sequence[str]) -> int:
    if len(argv) != 3:
        usage()
        return 1

    input_path = Path(argv[1])
    output_pdf = Path(argv[2])
    html_path = output_pdf.with_suffix(".html")

    metadata_raw, vlans_raw = load_payload(input_path)
    vlan_entries = build_vlan_entries(vlans_raw)
    metadata = build_metadata(metadata_raw, vlan_entries)

    icon_data_uri = load_icon_data_uri()
    render_html(vlan_entries, metadata, html_path, icon_data_uri)

    if not render_pdf_via_browser(html_path, output_pdf):
        lines = build_pdf_lines(vlan_entries, metadata)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        create_pdf(lines, str(output_pdf))

    print(f"HTML report: {html_path}")
    print(f"PDF report: {output_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
