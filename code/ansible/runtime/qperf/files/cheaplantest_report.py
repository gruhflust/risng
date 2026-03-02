#!/usr/bin/env python3
"""Render cheaplantest JSON results into HTML and PDF outputs."""
from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence


PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 36
FONT_SIZE = 9
LINE_HEIGHT = 12
REPORT_BANNER = "risng - Cloud Host Endpoint Analysis Probe"
REPORT_TITLE = "cheaplantest report"


def _format_datetime(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).isoformat(sep=" ", timespec="seconds")
        except ValueError:
            continue
    return value




def _group_results_by_test(results: Sequence[dict]) -> list[tuple[str, list[dict]]]:
    grouped: dict[str, list[dict]] = {}
    for entry in results:
        test_name = str(entry.get("test", "unknown"))
        grouped.setdefault(test_name, []).append(entry)
    grouped_items: list[tuple[str, list[dict]]] = []
    for test_name in sorted(grouped):
        entries = sorted(
            grouped[test_name],
            key=lambda item: (str(item.get("target", "")), str(item.get("address", ""))),
        )
        grouped_items.append((test_name, entries))
    return grouped_items


def _group_results_by_msg_size(results: Sequence[dict]) -> list[tuple[str, list[dict]]]:
    grouped: dict[str, list[dict]] = {}
    for entry in results:
        msg_size = str(entry.get("msg_size", "unspecified"))
        grouped.setdefault(msg_size, []).append(entry)
    grouped_items: list[tuple[str, list[dict]]] = []
    for msg_size in sorted(grouped):
        grouped_items.append((msg_size, grouped[msg_size]))
    return grouped_items

def build_html(report: dict) -> str:
    results = report.get("results") or []
    run_id = report.get("run_id", "")
    server_ip = report.get("server_ip", "")
    server_port = report.get("server_port", "")
    generated_at = report.get("generated_at", "")
    imix_profile = report.get("imix_profile") or {}
    imix_msg_sizes = imix_profile.get("msg_sizes") or []
    if not imix_msg_sizes and imix_profile.get("msg_size"):
        imix_msg_sizes = [imix_profile.get("msg_size")]
    imix_msg_size = ", ".join(str(v).strip() for v in imix_msg_sizes if str(v).strip())
    imix_explanation = (
        f"Packet size varies across the configured range: {imix_msg_size}."
        if imix_msg_size
        else "IMIX profile: no msg_size value found in report input."
    )

    rows = []
    grouped_by_profile = _group_results_by_msg_size(results)
    for msg_size, profile_entries in grouped_by_profile:
        rows.append(
            '<tr><td colspan="7" style="background:#dff5e3;font-weight:bold;">'
            + f"Data Sheet: msg_size={html.escape(msg_size)}"
            + "</td></tr>"
        )
        grouped_results = _group_results_by_test(profile_entries)
        for test_name, entries in grouped_results:
            rows.append(
                '<tr><td colspan="7" style="background:#eaf2ff;font-weight:bold;">'
                + f"Test Group: {html.escape(test_name)}"
                + "</td></tr>"
            )
            for entry in entries:
                rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(entry.get('target', '')))}</td>"
                    f"<td>{html.escape(str(entry.get('address', '')))}</td>"
                    f"<td>{html.escape(str(entry.get('vlan', '')))}</td>"
                    f"<td>{html.escape(str(entry.get('client_ip', '')))}</td>"
                    f"<td>{html.escape(str(entry.get('server_ip', '')))}</td>"
                    f"<td>{html.escape(str(entry.get('args', '')))}</td>"
                    f"<td><pre>{html.escape(str(entry.get('stdout', '')).strip())}</pre></td>"
                    "</tr>"
                )

    return f"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{REPORT_TITLE}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
header {{ margin-bottom: 16px; }}
summary {{ margin-bottom: 12px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #ccc; padding: 6px; vertical-align: top; }}
th {{ background: #f4f4f4; }}
pre {{ margin: 0; white-space: pre-wrap; }}
.code {{ font-family: "Courier New", monospace; }}
@page {{ size: A4 landscape; margin: 12mm; }}
.col-target {{ width: 10%; }}
.col-address {{ width: 10%; }}
.col-vlan {{ width: 6%; }}
.col-client {{ width: 10%; }}
.col-server {{ width: 10%; }}
.col-args {{ width: 14%; }}
.col-stdout {{ width: 40%; }}
</style>
</head>
<body>
<header>
  <h1>{REPORT_BANNER}</h1>
  <h2>{REPORT_TITLE}</h2>
  <div class="code">Run ID: {html.escape(str(run_id))}</div>
  <div class="code">Generated: {html.escape(str(generated_at))}</div>
  <div class="code">Server: {html.escape(str(server_ip))}:{html.escape(str(server_port))}</div>
  <div class="code">{html.escape(imix_explanation)}</div>
</header>
<table>
  <colgroup>
    <col class="col-target" />
    <col class="col-address" />
    <col class="col-vlan" />
    <col class="col-client" />
    <col class="col-server" />
    <col class="col-args" />
    <col class="col-stdout" />
  </colgroup>
  <thead>
    <tr>
      <th>Target</th>
      <th>Address</th>
      <th>VLAN</th>
      <th>Client IP</th>
      <th>Server IP</th>
      <th>Args</th>
      <th>Stdout</th>
    </tr>
  </thead>
  <tbody>
    {"\n".join(rows)}
  </tbody>
</table>
</body>
</html>
"""


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_pdf(lines: Sequence[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text_objects = []
    y = PAGE_HEIGHT - MARGIN
    for line in lines:
        if y <= MARGIN:
            text_objects.append("ET")
            text_objects.append("q")
            text_objects.append(f"0 0 {PAGE_WIDTH} {PAGE_HEIGHT} re W n")
            text_objects.append("Q")
            text_objects.append("BT")
            y = PAGE_HEIGHT - MARGIN
        text_objects.append(f"1 0 0 1 {MARGIN} {y} Tm ({escape_pdf_text(line)}) Tj")
        y -= LINE_HEIGHT

    content = "\n".join(["BT", f"/F1 {FONT_SIZE} Tf", *text_objects, "ET"])
    objects = []
    offsets = []

    def add_object(obj: str) -> None:
        offsets.append(sum(len(o) for o in objects) + 9)
        objects.append(obj)

    add_object("1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    add_object("2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    add_object(
        "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] ".format(
            w=PAGE_WIDTH, h=PAGE_HEIGHT
        )
        + "/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
    )
    add_object(f"4 0 obj<< /Length {len(content)} >>stream\n{content}\nendstream endobj\n")
    add_object("5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    xref_start = sum(len(o) for o in objects) + 9
    xref = ["xref", f"0 {len(objects) + 1}", "0000000000 65535 f "]
    for offset in offsets:
        xref.append(f"{offset:010d} 00000 n ")
    xref_data = "\n".join(xref)
    trailer = f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF"

    with output_path.open("wb") as handle:
        handle.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for obj in objects:
            handle.write(obj.encode("utf-8"))
        handle.write(xref_data.encode("utf-8"))
        handle.write(b"\n")
        handle.write(trailer.encode("utf-8"))


def render_pdf_via_browser(html_path: Path, pdf_path: Path) -> bool:
    candidates = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
    ]
    for binary in filter(None, candidates):
        try:
            subprocess.run(
                [
                    binary,
                    "--headless",
                    "--disable-gpu",
                    f"--print-to-pdf={pdf_path}",
                    "--print-to-pdf-no-header",
                    str(html_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if pdf_path.exists():
            return True
    return False


def build_pdf_lines(report: dict) -> list[str]:
    lines: list[str] = []
    imix_profile = report.get("imix_profile") or {}
    imix_msg_sizes = imix_profile.get("msg_sizes") or []
    if not imix_msg_sizes and imix_profile.get("msg_size"):
        imix_msg_sizes = [imix_profile.get("msg_size")]
    imix_msg_size = ", ".join(str(v).strip() for v in imix_msg_sizes if str(v).strip())
    imix_explanation = (
        f"Packet size varies across the configured range: {imix_msg_size}."
        if imix_msg_size
        else "IMIX profile: no msg_size value found in report input."
    )
    lines.append(REPORT_BANNER)
    lines.append(f"{REPORT_TITLE} - Run {report.get('run_id', '')}")
    lines.append(f"Generated: {report.get('generated_at', '')}")
    lines.append(f"Server: {report.get('server_ip', '')}:{report.get('server_port', '')}")
    lines.append(imix_explanation)
    lines.append("")
    grouped_by_profile = _group_results_by_msg_size(report.get("results") or [])
    for msg_size, profile_entries in grouped_by_profile:
        lines.append(f"Data Sheet: msg_size={msg_size}")
        lines.append("=" * 80)
        grouped_results = _group_results_by_test(profile_entries)
        for test_name, entries in grouped_results:
            lines.append(f"Test Group: {test_name}")
            lines.append("-" * 80)
            for entry in entries:
                lines.append(f"Target: {entry.get('target', '')} ({entry.get('address', '')})")
                lines.append(f"  VLAN: {entry.get('vlan', '')}")
                lines.append(f"  Args: {entry.get('args', '')}")
                stdout = str(entry.get('stdout', '')).strip()
                if stdout:
                    lines.append(f"  Stdout: {stdout}")
                lines.append("")
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: cheaplantest_report.py <input.json> <output.pdf>")
        return 1
    input_path = Path(sys.argv[1]).expanduser().resolve()
    pdf_path = Path(sys.argv[2]).expanduser().resolve()
    if not input_path.exists():
        print(f"Input JSON not found: {input_path}")
        return 1

    report = json.loads(input_path.read_text(encoding="utf-8"))
    html_path = pdf_path.with_suffix(".html")

    html_path.write_text(build_html(report), encoding="utf-8")

    if not render_pdf_via_browser(html_path, pdf_path):
        lines = build_pdf_lines(report)
        create_pdf(lines, pdf_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
