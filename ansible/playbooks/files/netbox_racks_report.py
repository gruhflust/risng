#!/usr/bin/env python3
"""Render NetBox rack data from JSON into HTML and PDF summaries."""
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
    ("Rack", 24),
    ("Site", 18),
    ("Location", 18),
    ("Role", 16),
    ("Status", 12),
    ("Identifiers", 20),
    ("Tags", 36),
]

TABLE_DIVIDER = "+" + "+".join("-" * (width + 2) for _, width in TABLE_COLUMNS) + "+"
TABLE_HEADER_DIVIDER = "+" + "+".join("=" * (width + 2) for _, width in TABLE_COLUMNS) + "+"
CARD_WIDTH = len(TABLE_DIVIDER)


def usage() -> None:
    print(
        "Usage: netbox_racks_report.py <input.json> <output.pdf>",
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
        # Allow legacy format which stores racks directly as a list.
        return {}, list(data)

    if not isinstance(data, dict):
        raise SystemExit("Input JSON must contain either a list or an object with 'racks'.")

    metadata = data.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    racks = data.get("racks")
    if not isinstance(racks, list):
        racks = []

    return metadata, racks


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
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: List[str] = []
    for tag in tags:
        lower = tag.lower()
        if lower in seen:
            continue
        seen.add(lower)
        deduped.append(tag)
    return deduped


def build_rack_entries(raw_racks: Sequence[dict]) -> List[dict]:
    entries: List[dict] = []
    for rack in raw_racks:
        if not isinstance(rack, dict):
            continue
        name = _text(rack.get("name"), default="<unnamed>")
        site = _text(rack.get("site"))
        location = _text(rack.get("location"))
        role = _text(rack.get("role"))
        status = _text(rack.get("status"), default="n/a")
        identifiers: List[str] = []
        asset_tag = _text(rack.get("asset_tag"))
        serial = _text(rack.get("serial"))
        if asset_tag:
            identifiers.append(f"Asset: {asset_tag}")
        if serial:
            identifiers.append(f"Serial: {serial}")
        height = rack.get("u_height")
        if height not in (None, ""):
            try:
                height_str = f"{int(height)}U"
            except (TypeError, ValueError):
                height_str = _text(height)
            identifiers.append(f"Height: {height_str}")
        tags = _collect_tags(rack.get("tags") or [])
        description = _text(rack.get("description"))

        entries.append(
            {
                "name": name,
                "site": site or "n/a",
                "location": location or "n/a",
                "role": role or "n/a",
                "status": status,
                "identifiers": identifiers,
                "tags": tags,
                "description": description,
            }
        )

    entries.sort(key=lambda item: (item["site"].lower(), item["location"].lower(), item["name"].lower()))
    return entries


def parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.utcnow()
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return datetime.utcnow()


def build_metadata(raw_meta: dict, racks: Sequence[dict]) -> dict:
    generated_at = parse_timestamp(_text(raw_meta.get("generated_at"), default=""))
    username = _text(raw_meta.get("username"), default="unknown user")
    base_url = _text(raw_meta.get("base_url"))
    rack_count = raw_meta.get("rack_count")
    try:
        total = int(rack_count)
    except (TypeError, ValueError):
        total = len(racks)

    title = _text(raw_meta.get("title"), default="NetBox Rack Overview")
    subtitle = _text(
        raw_meta.get("subtitle"),
        default=f"Racks for {username}",
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


def _wrap_identifiers(items: Sequence[str], width: int) -> List[str]:
    if not items:
        return ["—"]
    return _wrap_cell(" | ".join(items), width)


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


def build_pdf_table(racks: Sequence[dict]) -> List[str]:
    lines: List[str] = [TABLE_DIVIDER]
    header = [name.upper() for name, _ in TABLE_COLUMNS]
    lines.append(_format_table_line(header))
    lines.append(TABLE_HEADER_DIVIDER)

    for rack in racks:
        rack_name = _wrap_cell(rack["name"], TABLE_COLUMNS[0][1])
        site_lines = _wrap_cell(rack["site"], TABLE_COLUMNS[1][1])
        location_lines = _wrap_cell(rack["location"], TABLE_COLUMNS[2][1])
        role_lines = _wrap_cell(rack["role"], TABLE_COLUMNS[3][1])
        status_lines = _wrap_cell(rack["status"], TABLE_COLUMNS[4][1])
        identifiers_lines = _wrap_identifiers(rack["identifiers"], TABLE_COLUMNS[5][1])
        tags_lines = _wrap_tags(rack["tags"], TABLE_COLUMNS[6][1])

        max_lines = max(
            len(rack_name),
            len(site_lines),
            len(location_lines),
            len(role_lines),
            len(status_lines),
            len(identifiers_lines),
            len(tags_lines),
        )

        for index in range(max_lines):
            row = [
                rack_name[index] if index < len(rack_name) else "",
                site_lines[index] if index < len(site_lines) else "",
                location_lines[index] if index < len(location_lines) else "",
                role_lines[index] if index < len(role_lines) else "",
                status_lines[index] if index < len(status_lines) else "",
                identifiers_lines[index] if index < len(identifiers_lines) else "",
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


def build_pdf_lines(racks: Sequence[dict], metadata: dict) -> List[str]:
    lines: List[str] = []
    title = metadata.get("title", "NetBox Rack Overview")
    subtitle = metadata.get("subtitle", "")
    total = metadata.get("total", len(racks))
    timestamp = metadata.get("timestamp", "")
    base_url = metadata.get("base_url")

    lines.append("╔" + "═" * (CARD_WIDTH - 2) + "╗")
    lines.append(_card_line(title, CARD_WIDTH, align="center"))
    if subtitle:
        lines.append(_card_line(subtitle, CARD_WIDTH, align="center"))
    lines.append("╠" + "═" * (CARD_WIDTH - 2) + "╣")
    lines.append(_card_line(f"Total racks: {total}", CARD_WIDTH))
    if timestamp:
        lines.append(_card_line(f"Generated: {timestamp}", CARD_WIDTH))
    if base_url:
        lines.append(_card_line(f"Source: {base_url}", CARD_WIDTH))
    lines.append("╚" + "═" * (CARD_WIDTH - 2) + "╝")
    lines.append("")

    table_lines = build_pdf_table(racks)
    if table_lines:
        lines.extend(table_lines)
    else:
        lines.append("No rack entries present in the report.")

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


def render_html(racks: Sequence[dict], metadata: dict, output_path: Path, icon_data_uri: Optional[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[str] = []
    for rack in racks:
        tags = rack.get("tags") or []
        if tags:
            tag_html = "".join(f"<span class='tag'>{html.escape(tag)}</span>" for tag in tags)
        else:
            tag_html = "<span class='tag tag--empty'>No tags</span>"

        identifiers = rack.get("identifiers") or []
        if identifiers:
            ident_html = "".join(
                f"<span class='identifier'>{html.escape(identifier)}</span>" for identifier in identifiers
            )
        else:
            ident_html = "<span class='identifier identifier--empty'>No identifiers</span>"

        description = rack.get("description")
        if description:
            description_html = f"<p class='rack-description'>{html.escape(description)}</p>"
        else:
            description_html = ""

        rows.append(
            "<tr>"
            f"<td data-label='Rack'><span class='rack-name'>{html.escape(rack['name'])}</span>{description_html}</td>"
            f"<td data-label='Site'>{html.escape(rack['site'])}</td>"
            f"<td data-label='Location'>{html.escape(rack['location'])}</td>"
            f"<td data-label='Role'>{html.escape(rack['role'])}</td>"
            f"<td data-label='Status'>{html.escape(rack['status'])}</td>"
            f"<td data-label='Identifiers'>{ident_html}</td>"
            f"<td data-label='Tags'>{tag_html}</td>"
            "</tr>"
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
            "<h2>No racks returned from NetBox</h2>"
            "<p>Provide filters or adjust the NetBox query to populate this report.</p>"
            "</div>"
        )

    if icon_data_uri:
        icon_markup = f"<img src='{icon_data_uri}' alt='RISng logo' width='64' height='64' />"
    else:
        icon_markup = "<span class='report-initials' aria-hidden='true'>IS</span>"

    title = html.escape(metadata.get("title", "NetBox Rack Overview"))
    subtitle = html.escape(metadata.get("subtitle", ""))
    total = metadata.get("total", len(racks))
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
        --card-light: #ffffff;
        --card-dark: #1f2937;
        --text-light: #1f2937;
        --text-dark: #f9fafb;
        --muted-light: rgba(31, 41, 55, 0.6);
        --muted-dark: rgba(249, 250, 251, 0.65);
        --accent: #2563eb;
        --accent-muted: rgba(37, 99, 235, 0.15);
      }}

      body {{
        margin: 0;
        font-family: "Inter", "Segoe UI", Roboto, sans-serif;
        background: linear-gradient(135deg, var(--bg-light), #dde3f3);
        color: var(--text-light);
        padding: 2rem;
      }}

      @media (prefers-color-scheme: dark) {{
        body {{
          background: var(--bg-dark);
          color: var(--text-dark);
        }}
      }}

      .report {{
        max-width: 1200px;
        margin: 0 auto;
      }}

      .report-header {{
        display: flex;
        align-items: center;
        gap: 1.5rem;
        margin-bottom: 2rem;
      }}

      .report-initials {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border-radius: 16px;
        background: var(--accent);
        color: white;
        font-size: 1.5rem;
        font-weight: 600;
      }}

      h1 {{
        margin: 0;
        font-size: 2rem;
      }}

      .report-subtitle {{
        margin: 0.25rem 0 0;
        color: var(--muted-light);
      }}

      @media (prefers-color-scheme: dark) {{
        .report-subtitle {{
          color: var(--muted-dark);
        }}
      }}

      .report-meta {{
        margin-bottom: 1.5rem;
        padding: 1rem;
        border-radius: 12px;
        background: var(--card-light);
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
      }}

      @media (prefers-color-scheme: dark) {{
        .report-meta {{
          background: var(--card-dark);
          box-shadow: none;
        }}
      }}

      .meta-line {{
        margin: 0.25rem 0;
        font-size: 0.95rem;
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
        background: var(--card-light);
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
      }}

      @media (prefers-color-scheme: dark) {{
        table {{
          background: var(--card-dark);
          box-shadow: none;
        }}
      }}

      thead th {{
        text-align: left;
        padding: 0.85rem;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        background: var(--accent);
        color: #fff;
      }}

      tbody td {{
        padding: 0.9rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.25);
        vertical-align: top;
      }}

      tbody tr:last-child td {{
        border-bottom: none;
      }}

      .rack-name {{
        display: block;
        font-weight: 600;
        margin-bottom: 0.35rem;
      }}

      .rack-description {{
        margin: 0;
        font-size: 0.85rem;
        color: var(--muted-light);
      }}

      .identifier {{
        display: inline-flex;
        margin: 0.1rem;
        padding: 0.2rem 0.5rem;
        border-radius: 999px;
        background: var(--accent-muted);
        color: var(--accent);
        font-size: 0.8rem;
        font-weight: 500;
      }}

      .identifier--empty {{
        background: rgba(100, 116, 139, 0.15);
        color: rgba(100, 116, 139, 0.9);
      }}

      .tag {{
        display: inline-flex;
        align-items: center;
        margin: 0.1rem;
        padding: 0.2rem 0.5rem;
        border-radius: 999px;
        background: rgba(34, 197, 94, 0.15);
        color: #15803d;
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
        background: var(--card-light);
        box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
      }}

      @media (prefers-color-scheme: dark) {{
        .empty-state {{
          background: var(--card-dark);
          box-shadow: none;
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
        <p class='meta-line'><strong>Total racks:</strong> {total}</p>
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

    metadata_raw, racks_raw = load_payload(input_path)
    rack_entries = build_rack_entries(racks_raw)
    metadata = build_metadata(metadata_raw, rack_entries)

    icon_data_uri = load_icon_data_uri()
    render_html(rack_entries, metadata, html_path, icon_data_uri)

    if not render_pdf_via_browser(html_path, output_pdf):
        lines = build_pdf_lines(rack_entries, metadata)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        create_pdf(lines, str(output_pdf))

    print(f"HTML report: {html_path}")
    print(f"PDF report: {output_pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
