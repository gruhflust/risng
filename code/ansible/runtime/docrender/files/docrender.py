#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
from pathlib import Path
from typing import List

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except Exception:
    PIL_OK = False

CSS = """
body { font-family: Arial, sans-serif; margin: 22px; color: #111; }
h1,h2,h3 { margin-top: 1.2em; }
pre.code-bash {
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #333;
  overflow-x: auto;
}
code.inline { background: #f2f2f2; padding: 1px 4px; border-radius: 4px; }
table.md-table { border-collapse: collapse; margin: 10px 0; }
table.md-table th, table.md-table td { border: 1px solid #999; padding: 6px 8px; }
.table-render { margin: 8px 0 18px; }
.table-render img { border: 1px solid #ddd; max-width: 100%; }
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--out", required=True)
    return p.parse_args()


def is_table_header_sep(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", s))


def split_table_row(line: str) -> list[str]:
    s = line.strip().strip("|")
    return [c.strip() for c in s.split("|")]


def render_table_png(rows: list[list[str]], out_png: Path) -> bool:
    if not PIL_OK:
        return False
    font = ImageFont.load_default()
    pad_x, pad_y = 10, 8
    row_h = 22
    cols = max(len(r) for r in rows)
    widths = [0] * cols
    for r in rows:
        for i, cell in enumerate(r):
            w = len(cell) * 7 + 10
            widths[i] = max(widths[i], w)

    width = sum(widths) + (cols + 1)
    height = row_h * len(rows) + 1
    img = Image.new("RGB", (max(width, 320), max(height, 60)), "white")
    dr = ImageDraw.Draw(img)

    y = 0
    for ridx, r in enumerate(rows):
        x = 0
        bg = "#f2f2f2" if ridx == 0 else "white"
        for c in range(cols):
            cw = widths[c]
            dr.rectangle([x, y, x + cw, y + row_h], fill=bg, outline="#777")
            txt = r[c] if c < len(r) else ""
            dr.text((x + pad_x, y + pad_y), txt, fill="#111", font=font)
            x += cw
        y += row_h

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png)
    return True


def md_to_html(md: str, out_dir: Path, stem: str) -> str:
    lines = md.splitlines()
    html_parts: list[str] = []
    i = 0
    table_idx = 1

    while i < len(lines):
        line = lines[i]

        # fenced code blocks
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip().lower()
            i += 1
            block: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            cls = "code-bash" if lang == "bash" else ""
            html_parts.append(f"<pre class='{cls}'>{html.escape(chr(10).join(block))}</pre>")
            i += 1
            continue

        # markdown table
        if "|" in line and i + 1 < len(lines) and is_table_header_sep(lines[i + 1]):
            rows = [split_table_row(line)]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(split_table_row(lines[i]))
                i += 1

            # html table
            cols = max(len(r) for r in rows)
            thead = rows[0]
            body = rows[1:]
            t = ["<table class='md-table'>", "<thead><tr>"]
            for c in range(cols):
                t.append(f"<th>{html.escape(thead[c] if c < len(thead) else '')}</th>")
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>")
                for c in range(cols):
                    t.append(f"<td>{html.escape(r[c] if c < len(r) else '')}</td>")
                t.append("</tr>")
            t.append("</tbody></table>")
            html_parts.append("".join(t))

            # png render
            png_name = f"{stem}.table{table_idx}.png"
            png_path = out_dir / png_name
            if render_table_png(rows, png_path):
                html_parts.append(f"<div class='table-render'><img src='{html.escape(png_name)}' alt='table {table_idx}'/></div>")
            else:
                html_parts.append("<p><i>Table PNG render skipped (Pillow missing).</i></p>")
            table_idx += 1
            continue

        # headings
        if line.startswith("### "):
            html_parts.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            html_parts.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            html_parts.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.strip().startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            lis = "".join(f"<li>{html.escape(x)}</li>" for x in items)
            html_parts.append(f"<ul>{lis}</ul>")
            continue
        elif line.strip() == "":
            html_parts.append("")
        else:
            # inline code
            txt = re.sub(r"`([^`]+)`", lambda m: f"<code class='inline'>{html.escape(m.group(1))}</code>", html.escape(line))
            html_parts.append(f"<p>{txt}</p>")

        i += 1

    return "\n".join(html_parts)


def render_pdf_via_browser(html_path: Path, pdf_path: Path) -> bool:
    candidates = [shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("google-chrome")]
    for binary in filter(None, candidates):
        try:
            subprocess.run([
                binary,
                "--headless",
                "--disable-gpu",
                f"--print-to-pdf={pdf_path}",
                "--print-to-pdf-no-header",
                str(html_path),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=35)
            if pdf_path.exists():
                return True
        except Exception:
            continue
    return False


def create_fallback_pdf(md_text: str, pdf_path: Path) -> None:
    # Minimal valid PDF (text-only), similar fallback style used in cheap reports.
    page_w, page_h = 842, 595
    margin = 36
    line_h = 12
    font_size = 9

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = [ln.strip() for ln in md_text.splitlines() if ln.strip()][:320]
    y = page_h - margin
    text_ops: list[str] = []
    for ln in lines:
        if y <= margin:
            text_ops.append("ET")
            text_ops.append("BT")
            y = page_h - margin
        text_ops.append(f"1 0 0 1 {margin} {y} Tm ({esc(ln[:120])}) Tj")
        y -= line_h

    content = "\n".join(["BT", f"/F1 {font_size} Tf", *text_ops, "ET"])
    objs: list[str] = []
    offs: list[int] = []

    def add(obj: str) -> None:
        offs.append(sum(len(o) for o in objs) + 9)
        objs.append(obj)

    add("1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    add("2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    add(f"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_w} {page_h}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\\n")
    add(f"4 0 obj<< /Length {len(content)} >>stream\\n{content}\\nendstream endobj\\n")
    add("5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")

    xref_start = sum(len(o) for o in objs) + 9
    xref = ["xref", f"0 {len(objs)+1}", "0000000000 65535 f "] + [f"{o:010d} 00000 n " for o in offs]
    trailer = f"trailer<< /Size {len(objs)+1} /Root 1 0 R >>\\nstartxref\\n{xref_start}\\n%%EOF"

    with pdf_path.open("wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        for o in objs:
            f.write(o.encode("utf-8"))
        f.write("\n".join(xref).encode("utf-8"))
        f.write(b"\n")
        f.write(trailer.encode("utf-8"))


def main() -> int:
    args = parse_args()
    src = Path(args.source).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(f"Source directory missing: {src}")
        return 1

    md_files = sorted(src.rglob("*.md"))
    if not md_files:
        print(f"No markdown files in {src}")
        return 0

    for md_file in md_files:
        stem = md_file.stem
        md_text = md_file.read_text(encoding="utf-8", errors="ignore")
        body = md_to_html(md_text, out, stem)
        html_doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"

        html_path = out / f"{stem}.html"
        pdf_path = out / f"{stem}.pdf"

        html_path.write_text(html_doc, encoding="utf-8")
        if not render_pdf_via_browser(html_path, pdf_path):
            create_fallback_pdf(md_text, pdf_path)

        print(f"Rendered: {md_file.name} -> {html_path.name}, {pdf_path.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
