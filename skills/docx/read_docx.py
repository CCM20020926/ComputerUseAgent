"""Read a .docx file and output format-aware DSL code.

Usage:
    python read_docx.py <input_docx>

The output DSL can be passed directly to render.py to regenerate the document.
Captures:
  - Heading levels (Heading 1-9)
  - Inline formatting: bold, italic, underline, color (nestable)
  - Paragraph properties: alignment, font size (pt), first-line indent (chars)
  - Page breaks
  - Tables (with inline formatting inside cells)

Notes:
  - Images are NOT extracted (output as % [Image] comments).
  - Only explicitly set formatting is captured; style-inherited defaults are omitted.
  - List paragraphs are output as regular \\para commands.
"""

import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


# ──────────────────────── Low-level helpers ─────────────────────────


def _get_alignment(pPr) -> str | None:
    """Return alignment string ('center'|'left'|'right'|'justify') or None."""
    jc = pPr.find(qn("w:jc"))
    if jc is None:
        return None
    val = jc.get(qn("w:val"))
    return {
        "center": "center",
        "left": "left",
        "right": "right",
        "both": "justify",
        "justify": "justify",
    }.get(val)


def _get_font_size(rPr) -> float | None:
    """Return font size in pt from a w:rPr element, or None."""
    if rPr is None:
        return None
    sz = rPr.find(qn("w:sz"))
    if sz is None:
        return None
    val = sz.get(qn("w:val"))
    if val:
        try:
            return float(int(val) / 2)  # half-points → pt
        except ValueError:
            pass
    return None


def _get_indent(pPr) -> int | None:
    """Return first-line indent in character widths (approx), or None."""
    ind = pPr.find(qn("w:ind"))
    if ind is None:
        return None
    fl = ind.get(qn("w:firstLine"))
    if fl is None:
        return None
    try:
        twips = int(fl)
        return round(twips / 240)  # 240 twips ≈ 1 character width
    except ValueError:
        return None


def _get_font_name(rPr) -> str | None:
    """Return font name from w:rPr/w:rFonts, or None."""
    if rPr is None:
        return None
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        return None
    # Prefer ascii font, fall back to eastAsia for CJK
    return rFonts.get(qn("w:ascii")) or rFonts.get(qn("w:eastAsia"))


# ──────────────────────── Inline formatting ─────────────────────────


def _is_bold(rPr) -> bool:
    if rPr is None:
        return False
    b = rPr.find(qn("w:b"))
    if b is None:
        return False
    val = b.get(qn("w:val"))
    return val is None or val in ("true", "1")


def _is_italic(rPr) -> bool:
    if rPr is None:
        return False
    i = rPr.find(qn("w:i"))
    if i is None:
        return False
    val = i.get(qn("w:val"))
    return val is None or val in ("true", "1")


def _is_underline(rPr) -> bool:
    if rPr is None:
        return False
    u = rPr.find(qn("w:u"))
    if u is None:
        return False
    val = u.get(qn("w:val"))
    return val is not None and val not in ("none", "0")


def _get_color(rPr) -> str | None:
    """Return hex color string (e.g. 'FF0000') from w:rPr/w:color, or None."""
    if rPr is None:
        return None
    color_elem = rPr.find(qn("w:color"))
    if color_elem is None:
        return None
    val = color_elem.get(qn("w:val"))
    if val and len(val) == 6:
        try:
            int(val, 16)  # validate hex
            return val.upper()
        except ValueError:
            pass
    return None


def _format_run(text: str, rPr) -> str:
    """Wrap *text* with DSL inline-formatting tags derived from *rPr*."""
    if not text:
        return text
    result = text
    color = _get_color(rPr)
    if color:
        result = rf"\color{{{color}}}{{{result}}}"
    if _is_underline(rPr):
        result = rf"\u{{{result}}}"
    if _is_italic(rPr):
        result = rf"\i{{{result}}}"
    if _is_bold(rPr):
        result = rf"\b{{{result}}}"
    return result


# ──────────────────────── Paragraph-level formatting ────────────────


def _build_format_args(pPr, para_rPr=None, first_run_rPr=None) -> str:
    """Build the ``{...}`` format-args string for a paragraph/heading.

    Checks first run rPr (``first_run_rPr``) first for font size and name,
    then paragraph rPr (``para_rPr``), then paragraph-level rPr.
    Returns an empty string when no format args are found.
    """
    alignment = _get_alignment(pPr) if pPr is not None else None
    indent = _get_indent(pPr) if pPr is not None else None

    # Font size and name: prefer first run's rPr, then para rPr, then pPr's rPr
    font_size = None
    font_name = None
    if first_run_rPr is not None:
        font_size = _get_font_size(first_run_rPr)
        font_name = _get_font_name(first_run_rPr)
    if font_size is None and para_rPr is not None:
        font_size = _get_font_size(para_rPr)
    if font_name is None and para_rPr is not None:
        font_name = _get_font_name(para_rPr)
    if font_size is None and pPr is not None:
        rPr_in_pPr = pPr.find(qn("w:rPr"))
        font_size = _get_font_size(rPr_in_pPr)
    if font_name is None and pPr is not None:
        rPr_in_pPr = pPr.find(qn("w:rPr"))
        font_name = _get_font_name(rPr_in_pPr)

    parts: list[str] = []
    if alignment:
        parts.append(alignment)
    if font_size is not None:
        parts.append(str(int(font_size)) if font_size == int(font_size) else str(font_size))
    if indent is not None and indent > 0:
        parts.append(f"indent={indent}")
    if font_name:
        parts.append(f"font={font_name}")

    return ",".join(parts)


# ──────────────────────── Block-level readers ───────────────────────


def _read_paragraph(paragraph) -> str | None:
    """Return DSL lines for one paragraph, or None if empty/unrecognised."""
    style_name = paragraph.style.name if paragraph.style else ""

    # Detect heading level
    heading_level = None
    if style_name.startswith("Heading"):
        try:
            heading_level = int(style_name.split()[-1])
        except (ValueError, IndexError):
            pass
    elif style_name == "Title":
        heading_level = 1

    # Collect inline-formatted text segments; track first run's rPr for font info
    segments: list[str] = []
    first_run_rPr = None
    for run in paragraph.runs:
        # Page break inside a run
        for br in run._element.findall(qn("w:br")):
            if br.get(qn("w:type")) == "page":
                segments.append("__PAGEBREAK__")
        text = run.text or ""
        if text:
            rPr = run._element.find(qn("w:rPr"))
            if first_run_rPr is None:
                first_run_rPr = rPr
            segments.append(_format_run(text, rPr))

    # Extract paragraph-level format args
    pPr = paragraph._element.find(qn("w:pPr"))
    para_rPr = pPr.find(qn("w:rPr")) if pPr is not None else None
    fmt_args = _build_format_args(pPr, para_rPr, first_run_rPr)
    fmt_block = f"{{{fmt_args}}}" if fmt_args else ""

    # Heading
    if heading_level is not None:
        text = "".join(segments)
        line = rf"\heading{{{text}}}{{{heading_level}}}"
        if fmt_block:
            line += fmt_block
        return line

    # Check for page-break-only paragraph
    if not any(s != "__PAGEBREAK__" for s in segments):
        if "__PAGEBREAK__" in segments:
            return r"\pagebreak"
        return None  # truly empty paragraph

    # Regular paragraph
    text = "".join(segments)
    line = rf"\para{{{text}}}"
    if fmt_block:
        line += fmt_block
    return line


def _read_table(table) -> str:
    """Return DSL lines for one table (including \\begin{table} / \\end{table})."""
    lines = [r"\begin{table}"]
    for row in table.rows:
        lines.append(r"\row")
        for cell in row.cells:
            cell_parts: list[str] = []
            for para in cell.paragraphs:
                for run in para.runs:
                    text = run.text or ""
                    if text:
                        rPr = run._element.find(qn("w:rPr"))
                        cell_parts.append(_format_run(text, rPr))
            lines.append(rf"\cell{{{''.join(cell_parts)}}}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ──────────────────────── Document reader ───────────────────────────


def read_docx(path: str) -> str:
    """Read *path* and return the full DSL representation."""
    doc = Document(path)
    output: list[str] = []

    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "tbl":
            from docx.table import Table
            output.append(_read_table(Table(child, doc)))

        elif tag == "p":
            from docx.text.paragraph import Paragraph
            result = _read_paragraph(Paragraph(child, doc))
            if result:
                # A paragraph may produce multiple lines (e.g. pagebreak + text)
                output.append(result)

    return "\n".join(output)


# ──────────────────────── Entry point ───────────────────────────────


def main():
    if len(sys.argv) != 2:
        print("Usage: python read_docx.py <input_docx>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    dsl = read_docx(str(input_path))
    print(dsl)


if __name__ == "__main__":
    main()
