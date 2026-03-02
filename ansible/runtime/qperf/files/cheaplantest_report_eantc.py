#!/usr/bin/env python3
"""Render cheaplantest_eantc JSON results into HTML and PDF outputs.

This is a parallel variant of cheaplantest_report.py.
Goal: keep report *format/style* identical, but add:
- a clear header note that the EANTC mix was used
- a rendered EANTC mix appendix at the end of the PDF/HTML

Usage:
  cheaplantest_report_eantc.py <input.json> <output.pdf>
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence
import re


PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 36
FONT_SIZE = 9
LINE_HEIGHT = 12
REPORT_BANNER = "risng - Cloud Host Endpoint Analysis Probe"
REPORT_TITLE = "cheaplantest_eantc report"
HEADER_NOTE = "NOTE: EANTC traffic mix enabled (IMIX with Jumbo Frame)"


def eantc_mix_lines() -> list[str]:
    rows = [
        (60, 78, 5243, "7.38%", "52.42%"),
        (132, 150, 861, "2.33%", "8.61%"),
        (296, 314, 273, "1.55%", "2.73%"),
        (468, 486, 233, "2.04%", "2.33%"),
        (557, 575, 230, "2.39%", "2.30%"),
        (952, 970, 127, "2.22%", "1.27%"),
        (1010, 1028, 151, "2.80%", "1.51%"),
        (1500, 1518, 2882, "78.97%", "28.81%"),
        (8800, 8818, 2, "0.32%", "0.02%"),
    ]

    lines = [
        "",
        "EANTC MIX (rendered)",
        "=" * 80,
        f"{'pkt[B]':>6}  {'frame[B]':>7}  {'weight':>6}  {'bw% L2':>8}  {'count%':>8}",
        "-" * 80,
    ]
    for pkt, frame, weight, bw, cnt in rows:
        lines.append(f"{pkt:6d}  {frame:7d}  {weight:6d}  {bw:>8}  {cnt:>8}")

    lines += [
        "-" * 80,
        "Totals: weight=10002, avg_frame_size_L2=553.91B",
        "qperf msg_size mix:",
        "  60:60:*5243,132:132:*861,296:296:*273,468:468:*233,557:557:*230,952:952:*127,1010:1010:*151,1500:1500:*2882,8800:8800:*2",
    ]
    return lines


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

    mix_html = "<hr/><h3>EANTC mix (rendered)</h3><pre>" + html.escape("\n".join(eantc_mix_lines())) + "</pre>"
    summary_html = "<hr/><h3>EANTC mix summary (weighted)</h3><pre>" + html.escape("\n".join(build_tcp_udp_summary_lines(report))) + "</pre>"

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
.note {{ padding: 8px 10px; background: #fff4cc; border: 1px solid #f0d27a; }}
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
  <div class="note"><b>{html.escape(HEADER_NOTE)}</b></div>
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
{mix_html}
{summary_html}
</body>
</html>
"""


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def parse_metric_from_stdout(stdout: str) -> tuple[float | None, str | None]:
    """Extract first numeric + unit token from qperf stdout.

    Examples:
      "tcp_bw:  9.42 Gbit/s" -> (9.42, "Gbit/s")
      "tcp_lat:  12.3 us" -> (12.3, "us")

    Returns (value, unit) or (None, None).
    """
    if not stdout:
        return None, None
    # take first line with a number
    for line in str(stdout).splitlines():
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z/]+)", line)
        if m:
            return float(m.group(1)), m.group(2)
    return None, None


def normalize_metric(value: float, unit: str) -> tuple[float, str] | None:
    """Normalize metric to a base unit.

    - bandwidth -> bytes_per_s
    - latency   -> usec

    Handles qperf-like outputs such as:
      - 2.61 GB/sec
      - 957 MB/sec
      - 26.4 Gbit/s
      - 12.3 us / 0.051 ms

    Returns (base_value, base_kind) where base_kind in {"bytes_per_s", "usec"}.
    """
    u = (unit or "").strip()
    if not u:
        return None

    # latency
    ul = u.lower()
    if ul in ("us", "usec"):
        return value, "usec"
    if ul in ("ms", "msec"):
        return value * 1000.0, "usec"
    if ul in ("s", "sec"):
        return value * 1_000_000.0, "usec"

    # bandwidth: parse bit/byte with SI prefixes
    m = re.search(r"^([kKmMgGtT]?)([bB])(?:it|yte)?(?:/s|/sec|ps)?$", u)
    if not m:
        # sometimes unit token is like "GB/sec" already; above should catch,
        # but keep a safe fallback by stripping whitespace.
        m = re.search(r"([kKmMgGtT]?)([bB])", u)
    if not m:
        return None

    prefix = (m.group(1) or "").upper()
    b_or_B = m.group(2)
    factor = {"": 1.0, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}.get(prefix, 1.0)

    if b_or_B == "B":
        return value * factor, "bytes_per_s"

    # bits -> bytes
    return (value * factor) / 8.0, "bytes_per_s"


def msg_size_weight(msg_size: str) -> int:
    # msg_size is like "60:60:*5243"; weight is after '*'
    if not msg_size:
        return 0
    m = re.search(r"\*(\d+)", msg_size)
    return int(m.group(1)) if m else 0


def weighted_mean_for_test_and_target(report: dict, test_name: str, target: str) -> tuple[float | None, str | None]:
    """Compute weighted mean over msg_size for a given (test,target).

    - For each msg_size: average across paths (VLAN) if multiple exist
    - Then apply EANTC msg_size weights

    Returns (base_value, base_kind) with base_kind in {"bytes_per_s","usec"}.
    """
    results = report.get("results") or []

    buckets: dict[str, list[tuple[float, str]]] = {}
    for entry in results:
        if str(entry.get("test", "")) != test_name:
            continue
        if str(entry.get("target", "")) != target:
            continue
        if int(entry.get("rc", 0) or 0) != 0:
            continue
        msg = str(entry.get("msg_size", ""))
        val, unit = parse_metric_from_stdout(str(entry.get("stdout", "")))
        if val is None or unit is None:
            continue
        base = normalize_metric(val, unit)
        if not base:
            continue
        buckets.setdefault(msg, []).append(base)

    # mean per msg_size (across VLAN paths if present)
    per_msg: dict[str, tuple[float, str]] = {}
    for msg, vals in buckets.items():
        if not vals:
            continue
        kind = vals[0][1]
        mean = sum(v for v, _ in vals) / len(vals)
        per_msg[msg] = (mean, kind)

    # weighted mean over msg_size
    acc = 0.0
    wsum = 0
    kind: str | None = None
    for msg, (mean, k) in per_msg.items():
        w = msg_size_weight(msg)
        if w <= 0:
            continue
        kind = kind or k
        acc += mean * w
        wsum += w

    if wsum <= 0 or kind is None:
        return None, None

    return acc / wsum, kind


def report_targets(report: dict) -> list[str]:
    targets = sorted({str(r.get('target','')) for r in (report.get('results') or []) if str(r.get('target',''))})
    return targets


def format_bandwidth(bytes_per_s: float) -> tuple[str, str]:
    # show like qperf: MB/sec or GB/sec
    gb = bytes_per_s / 1e9
    mb = bytes_per_s / 1e6
    if gb >= 1.0:
        return f"{gb:.2f}", "GB/sec"
    return f"{mb:.0f}", "MB/sec"


def format_latency_usec(usec: float) -> tuple[str, str]:
    ms = usec / 1000.0
    # keep similar precision as existing report
    return f"{ms:.3f}", "ms"


def build_tcp_udp_summary_lines(report: dict) -> list[str]:
    """Two summary tables (TCP and UDP), grouped per target host.

    For each target:
      - compute weighted mean across msg_size for bandwidth and latency
      - keep units aligned with qperf-style output

    This avoids a single grand-total aggregation which is hard to use.
    """
    mapping = {
        "TCP": {
            "bandwidth": "tcp_bandwidth_imix",
            "latency": "tcp_latency_imix",
        },
        "UDP": {
            "bandwidth": "udp_bandwidth_imix",
            "latency": "udp_latency_imix",
        },
    }

    targets = report_targets(report)

    lines: list[str] = [
        "",
        "EANTC MIX SUMMARY (weighted averages)",
        "=" * 80,
        "(per target: per msg_size avg over paths; then weighted by EANTC msg_size weights)",
    ]

    for proto in ("TCP", "UDP"):
        lines.append("")
        lines.append(f"{proto} SUMMARY (per target)")
        lines.append("-" * 80)
        lines.append(f"{'target':14}  {'bw':>12}  {'unit':>10}  {'lat':>10}  {'unit':>6}")
        lines.append("-" * 80)

        # also compute overall mean over targets (of already-weighted per-target means)
        bw_vals: list[float] = []
        lat_vals: list[float] = []

        for t in targets:
            bw_val, bw_kind = weighted_mean_for_test_and_target(report, mapping[proto]["bandwidth"], t)
            lat_val, lat_kind = weighted_mean_for_test_and_target(report, mapping[proto]["latency"], t)

            if bw_val is not None and bw_kind == "bytes_per_s":
                v_bw, u_bw = format_bandwidth(bw_val)
                bw_vals.append(bw_val)
            else:
                v_bw, u_bw = "n/a", ""

            if lat_val is not None and lat_kind == "usec":
                v_lat, u_lat = format_latency_usec(lat_val)
                lat_vals.append(lat_val)
            else:
                v_lat, u_lat = "n/a", ""

            lines.append(f"{t[:14]:14}  {v_bw:>12}  {u_bw:>10}  {v_lat:>10}  {u_lat:>6}")

        def mean(xs: list[float]) -> float | None:
            return (sum(xs) / len(xs)) if xs else None

        lines.append("-" * 80)
        bw_m = mean(bw_vals)
        lat_m = mean(lat_vals)
        if bw_m is not None:
            v_bw, u_bw = format_bandwidth(bw_m)
        else:
            v_bw, u_bw = "n/a", ""
        if lat_m is not None:
            v_lat, u_lat = format_latency_usec(lat_m)
        else:
            v_lat, u_lat = "n/a", ""
        lines.append(f"{'MEAN':14}  {v_bw:>12}  {u_bw:>10}  {v_lat:>10}  {u_lat:>6}")

    lines.append("")
    return lines


def create_pdf(lines: Sequence[str], output_path: Path) -> None:
    # Same PDF style generator as cheaplantest_report.py
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
        "3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] ".format(w=PAGE_WIDTH, h=PAGE_HEIGHT)
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
    # Same structure as cheaplantest_report.py, with appended mix section.
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
    lines.append(HEADER_NOTE)
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
                stdout = str(entry.get("stdout", "")).strip()
                if stdout:
                    lines.append(f"  Stdout: {stdout}")
                lines.append("")

    lines.extend(eantc_mix_lines())
    lines.extend(build_tcp_udp_summary_lines(report))
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: cheaplantest_report_eantc.py <input.json> <output.pdf>")
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
