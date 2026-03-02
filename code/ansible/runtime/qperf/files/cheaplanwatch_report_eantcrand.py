#!/usr/bin/env python3
"""cheaplanwatch_report_eantcrand.py

Report for randomized EANTC IMIX cheaplanwatch runs.
Unlike legacy/eantc reports, this variant focuses on cumulative/summary values
and includes a legend describing the randomization.

Usage:
  cheaplanwatch_report_eantcrand.py <input.json> <output.pdf>
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BANNER = "risng - Cloud Host Endpoint Analysis Probe"
TITLE = "cheaplanwatch_eantcrand report"
HEADER_NOTE = "NOTE: EANTC traffic mix enabled (randomized per-sample selection)"

PAGE_WIDTH = 842
PAGE_HEIGHT = 595
MARGIN = 36
FONT_SIZE = 9
LINE_HEIGHT = 12


def eantc_mix_lines() -> list[str]:
    # same rendered legend as _eantc
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


def parse_number_unit(s: str) -> tuple[float | None, str | None]:
    if not s:
        return None, None
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z/]+)", str(s))
    if not m:
        return None, None
    return float(m.group(1)), m.group(2)


def to_bytes_per_s(v: float, unit: str) -> float | None:
    u = unit.strip()
    m = re.search(r"^([kKmMgGtT]?)([bB])(?:it|yte)?(?:/s|/sec|ps)?$", u)
    if not m:
        m = re.search(r"([kKmMgGtT]?)([bB])", u)
    if not m:
        return None
    prefix = (m.group(1) or "").upper()
    b_or_B = m.group(2)
    factor = {"": 1.0, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12}.get(prefix, 1.0)
    if b_or_B == "B":
        return v * factor
    return (v * factor) / 8.0


def format_bw(bytes_per_s: float) -> str:
    gb = bytes_per_s / 1e9
    mb = bytes_per_s / 1e6
    if gb >= 1.0:
        return f"{gb:.2f} GB/sec"
    return f"{mb:.0f} MB/sec"


def parse_latency_to_ms(s: str) -> float | None:
    v, u = parse_number_unit(s)
    if v is None or u is None:
        return None
    ul = u.lower()
    if ul in ("us", "usec"):
        return v / 1000.0
    if ul in ("ms", "msec"):
        return v
    if ul in ("s", "sec"):
        return v * 1000.0
    return None


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def summarize_client(client: dict[str, Any]) -> dict[str, Any]:
    bws: list[float] = []
    lats: list[float] = []
    for s in client.get("samples", []) or []:
        v, u = parse_number_unit(s.get("tcp_bw", ""))
        if v is not None and u is not None:
            b = to_bytes_per_s(v, u)
            if b is not None:
                bws.append(b)
        ms = parse_latency_to_ms(s.get("tcp_lat", ""))
        if ms is not None:
            lats.append(ms)

    bw_m = mean(bws)
    lat_m = mean(lats)
    return {
        "host": client.get("host", ""),
        "mode": client.get("mode", ""),
        "seed": (client.get("seed") if isinstance(client.get("seed"), int) else None),
        "samples": len(client.get("samples", []) or []),
        "tcp_bw_mean": format_bw(bw_m) if bw_m is not None else "n/a",
        "tcp_lat_mean_ms": f"{lat_m:.3f} ms" if lat_m is not None else "n/a",
        "observed": (client.get("imix", {}) or {}).get("observed_count", {}),
    }


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
    lines = [BANNER, f"{TITLE} - run {data.get('run_id','')}", HEADER_NOTE, ""]

    clients = [summarize_client(c) for c in (data.get("clients", []) or [])]

    lines.append("SUMMARY (per host)")
    lines.append("=" * 80)
    lines.append(f"{'host':14}  {'samples':>7}  {'tcp_bw_mean':>14}  {'tcp_lat_mean':>14}")
    lines.append("-" * 80)
    for c in clients:
        lines.append(
            f"{str(c.get('host',''))[:14]:14}  {c.get('samples',0):7d}  {str(c.get('tcp_bw_mean','')):>14}  {str(c.get('tcp_lat_mean_ms','')):>14}"
        )

    lines.extend(eantc_mix_lines())
    lines += [
        "",
        "RANDOMIZATION LEGEND",
        "=" * 80,
        "Per sample we draw one msg_size according to EANTC weights (probability proportional to weight).",
        f"Seed is stored per client payload (deterministic if CHEAPLANWATCH_SEED is set).",
        "Observed counts per msg_size are recorded in JSON (imix.observed_count).",
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
        print("Usage: cheaplanwatch_report_eantcrand.py <input.json> <output.pdf>")
        return 1
    src = Path(sys.argv[1])
    out_pdf = Path(sys.argv[2])
    out_html = out_pdf.with_suffix(".html")
    data = json.loads(src.read_text(encoding="utf-8"))
    out_html.write_text(build_html(data), encoding="utf-8")
    if not render_pdf_via_browser(out_html, out_pdf):
        create_pdf(build_lines(data), out_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
