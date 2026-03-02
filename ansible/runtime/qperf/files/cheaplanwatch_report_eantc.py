#!/usr/bin/env python3
"""Render cheaplanwatch_eantc aggregate JSON into HTML + PDF.

Parallel variant of cheaplanwatch_report.py to keep legacy output unchanged.
Adds:
- a clear header note that the EANTC mix was used
- a rendered EANTC mix appendix at the end of the PDF/HTML

Usage:
  cheaplanwatch_report_eantc.py <input.json> <output.pdf>
"""

from __future__ import annotations

import html
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

BANNER = "risng - Cloud Host Endpoint Analysis Probe"
TITLE = "cheaplanwatch_eantc report"
HEADER_NOTE = "NOTE: EANTC traffic mix enabled (IMIX with Jumbo Frame)"

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


def create_pdf(lines: Sequence[str], output_path: Path) -> None:
    # Same PDF style generator as cheaplanwatch_report.py
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
        if pdf_path.exists():
            return True
    return False


def build_html(data: dict) -> str:
    rows = []
    for host in data.get("clients", []):
        b = host.get("baseline", {})
        target = host.get("target") or host.get("host") or "unknown"
        addr = host.get("address", "")
        rows.append(
            "<tr style='background:#eef3ff'><td colspan='6'><b>"
            + html.escape(str(target))
            + "</b> ("
            + html.escape(str(addr))
            + ") | baseline bw="
            + html.escape(str(b.get("tcp_bw", "")))
            + " lat="
            + html.escape(str(b.get("tcp_lat", "")))
            + " iperf="
            + html.escape(str(b.get("iperf_bw", "")))
            + " ping="
            + html.escape(str(b.get("ping_avg", "")))
            + "/"
            + html.escape(str(b.get("ping_jitter", "")))
            + "</td></tr>"
        )
        for s in host.get("samples", [])[-40:]:
            rows.append(
                "<tr>"
                + "".join(
                    f"<td>{html.escape(str(s.get(k, '')))}</td>" for k in ["ts_iso", "ts_epoch", "tcp_bw", "tcp_lat", "ping_avg", "ping_jitter"]
                )
                + "<td>live</td></tr>"
            )

    mix_html = "<hr/><h3>EANTC mix (rendered)</h3><pre>" + html.escape("\n".join(eantc_mix_lines())) + "</pre>"

    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{TITLE}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
.note {{ padding: 8px 10px; background: #fff4cc; border: 1px solid #f0d27a; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #ccc; padding: 6px; vertical-align: top; }}
th {{ background: #f4f4f4; }}
@page {{ size: A4 landscape; margin: 12mm; }}
</style>
</head>
<body>
<h1>{BANNER}</h1>
<h2>{TITLE}</h2>
<div class='note'><b>{html.escape(HEADER_NOTE)}</b></div>
<p>run_id={html.escape(str(data.get('run_id','')))} | generated_at={html.escape(str(data.get('generated_at','')))}</p>
<table>
<tr><th>ts_iso</th><th>ts_epoch</th><th>tcp_bw</th><th>tcp_lat</th><th>ping_avg</th><th>ping_jitter</th><th>kind</th></tr>
{''.join(rows)}
</table>
{mix_html}
</body></html>"""


def build_pdf_lines(data: dict) -> list[str]:
    # Same structure as cheaplanwatch_report.py, with appended mix section.
    lines = [BANNER, f"{TITLE} - run {data.get('run_id','')}", HEADER_NOTE, ""]
    for host in data.get("clients", []):
        b = host.get("baseline", {})
        target = host.get("target") or host.get("host") or "unknown"
        lines.append(f"Host: {target} ({host.get('address','')})")
        lines.append(
            f"  Baseline bw={b.get('tcp_bw','')} lat={b.get('tcp_lat','')} iperf={b.get('iperf_bw','')} ping={b.get('ping_avg','')}/{b.get('ping_jitter','')}"
        )
        for s in host.get("samples", [])[-20:]:
            lines.append(
                f"  {s.get('ts_iso', s.get('ts_epoch',''))} bw={s.get('tcp_bw','')} lat={s.get('tcp_lat','')} ping={s.get('ping_avg','')}/{s.get('ping_jitter','')}"
            )
        lines.append("")

    lines.extend(eantc_mix_lines())
    return lines


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: cheaplanwatch_report_eantc.py <input.json> <output.pdf>")
        return 1
    src = Path(sys.argv[1])
    out_pdf = Path(sys.argv[2])
    out_html = out_pdf.with_suffix(".html")
    data = json.loads(src.read_text(encoding="utf-8"))
    out_html.write_text(build_html(data), encoding="utf-8")
    if not render_pdf_via_browser(out_html, out_pdf):
        create_pdf(build_pdf_lines(data), out_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
