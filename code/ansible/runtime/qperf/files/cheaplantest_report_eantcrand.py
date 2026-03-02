#!/usr/bin/env python3
"""cheaplantest_report_eantcrand.py

Report for randomized/quota-shuffled EANTC mix cheaplantest runs.
This variant intentionally does NOT render all per-msg_size measurements.
It renders:
- legend describing the EANTC mix
- legend describing the quota deck shuffle method
- cumulative summary tables for TCP and UDP (bw + lat)

Usage:
  cheaplantest_report_eantcrand.py <input.json> <output.pdf>
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BANNER = "risng - Cloud Host Endpoint Analysis Probe"
TITLE = "cheaplantest_eantcrand report"
HEADER_NOTE = "NOTE: EANTC traffic mix enabled (quota deck shuffle per host)"

PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 36
FONT_SIZE = 9
LINE_HEIGHT = 12


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


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def create_pdf(lines: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text_objects: list[str] = []
    y = PAGE_HEIGHT - MARGIN
    for line in lines:
        if y <= MARGIN:
            text_objects.append("ET")
            text_objects.append("BT")
            y = PAGE_HEIGHT - MARGIN
        text_objects.append(f"1 0 0 1 {MARGIN} {y} Tm ({escape_pdf_text(line)}) Tj")
        y -= LINE_HEIGHT

    content = "\n".join(["BT", f"/F1 {FONT_SIZE} Tf", *text_objects, "ET"])

    objects: list[str] = []
    offsets: list[int] = []

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
    trailer = f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF"

    with output_path.open("wb") as handle:
        handle.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for obj in objects:
            handle.write(obj.encode("utf-8"))
        handle.write("\n".join(xref).encode("utf-8"))
        handle.write(b"\n")
        handle.write(trailer.encode("utf-8"))


def render_pdf_via_browser(html_path: Path, pdf_path: Path) -> bool:
    candidates = [shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("google-chrome")]
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
                timeout=25,
            )
        except Exception:
            continue
        return pdf_path.exists()
    return False


def build_lines(data: dict[str, Any]) -> list[str]:
    lines = [
        BANNER,
        f"{TITLE} - run {data.get('run_id','')}",
        HEADER_NOTE,
        f"Generated: {data.get('generated_at','')}",
        f"Server: {data.get('server_ip','')}:{data.get('server_port','')}",
        "",
    ]

    def fmt_bw(bps: float | None) -> str:
        if bps is None:
            return "n/a"
        gb = bps / 1e9
        mb = bps / 1e6
        if gb >= 1.0:
            return f"{gb:.2f} GB/sec"
        return f"{mb:.0f} MB/sec"

    def fmt_lat(usec: float | None) -> str:
        if usec is None:
            return "n/a"
        return f"{(usec/1000.0):.3f} ms"

    # Per host summary (pattern like cheaplantest_eantc summary)
    hosts = list(data.get("hosts", []) or [])

    tcp_bw_list: list[float] = []
    tcp_lat_list: list[float] = []
    udp_bw_list: list[float] = []
    udp_lat_list: list[float] = []

    lines.append("TCP SUMMARY (per target)")
    lines.append("=" * 80)
    lines.append(f"{'target':14}  {'bw':>12}  {'lat':>10}")
    lines.append("-" * 80)
    for h in hosts:
        target = str(h.get("host") or h.get("target") or "unknown")[:14]
        means = (h.get("means") or {})
        tb = means.get("tcp_bw_bytes_per_s")
        tl = means.get("tcp_lat_usec")
        if isinstance(tb, (int, float)):
            tcp_bw_list.append(float(tb))
        if isinstance(tl, (int, float)):
            tcp_lat_list.append(float(tl))
        lines.append(
            f"{target:14}  {fmt_bw(float(tb) if isinstance(tb,(int,float)) else None):>12}"
            f"  {fmt_lat(float(tl) if isinstance(tl,(int,float)) else None):>10}"
        )

    lines.append("")
    lines.append("UDP SUMMARY (per target)")
    lines.append("=" * 80)
    lines.append(f"{'target':14}  {'bw':>12}  {'lat':>10}")
    lines.append("-" * 80)
    for h in hosts:
        target = str(h.get("host") or h.get("target") or "unknown")[:14]
        means = (h.get("means") or {})
        ub = means.get("udp_bw_bytes_per_s")
        ul = means.get("udp_lat_usec")
        if isinstance(ub, (int, float)):
            udp_bw_list.append(float(ub))
        if isinstance(ul, (int, float)):
            udp_lat_list.append(float(ul))
        lines.append(
            f"{target:14}  {fmt_bw(float(ub) if isinstance(ub,(int,float)) else None):>12}"
            f"  {fmt_lat(float(ul) if isinstance(ul,(int,float)) else None):>10}"
        )

    def mean(xs: list[float]) -> float | None:
        return (sum(xs) / len(xs)) if xs else None

    # Overall summary (mean over hosts)
    lines += ["", "OVERALL (mean over hosts)", "-" * 80]
    lines.append(f"TCP bw: {fmt_bw(mean(tcp_bw_list))} | TCP lat: {fmt_lat(mean(tcp_lat_list))}")
    lines.append(f"UDP bw: {fmt_bw(mean(udp_bw_list))} | UDP lat: {fmt_lat(mean(udp_lat_list))}")

    lines.extend(eantc_mix_lines())

    legend = data.get("legend", {}) or {}
    lines += [
        "",
        "RANDOMIZATION LEGEND",
        "=" * 80,
        "Method: quota deck shuffle per host.",
        "We build a deck of msg_size entries proportional to EANTC weights (scaled), shuffle it,",
        "then draw sequentially. When deck is empty, we reshuffle a new deck.",
        f"Duration per host: {legend.get('duration_sec','?')} sec",
        f"Deck scale: {legend.get('deck_scale','?')} (weights divided by scale and rounded)",
        f"Seed: {legend.get('seed','?')} (deterministic per run_id)",
    ]

    return lines


def build_html(data: dict[str, Any]) -> str:
    lines = "\n".join(build_lines(data))
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{TITLE}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
.note {{ padding: 8px 10px; background: #fff4cc; border: 1px solid #f0d27a; }}
pre {{ white-space: pre-wrap; }}
@page {{ size: A4 landscape; margin: 12mm; }}
</style></head><body>
<h1>{BANNER}</h1>
<h2>{TITLE}</h2>
<div class='note'><b>{html.escape(HEADER_NOTE)}</b></div>
<pre>{html.escape(lines)}</pre>
</body></html>"""


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: cheaplantest_report_eantcrand.py <input.json> <output.pdf>")
        return 1
    src = Path(sys.argv[1])
    out_pdf = Path(sys.argv[2])
    out_html = out_pdf.with_suffix('.html')
    data = json.loads(src.read_text(encoding='utf-8'))
    out_html.write_text(build_html(data), encoding='utf-8')
    if not render_pdf_via_browser(out_html, out_pdf):
        create_pdf(build_lines(data), out_pdf)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
