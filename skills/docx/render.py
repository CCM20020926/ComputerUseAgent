"""Render a .docx document from a LaTeX-like DSL script.

Usage:
    python render.py <dsl_code> <output_path>

DSL syntax:
    \\heading{Title}              H1 heading
    \\heading{Title}{2}           H2 heading (level 0-9)
    \\heading{Title}{center,16}   H1 with alignment + font size (pt)
    \\para{Body text}             Paragraph
    \\para{text}{indent=2}        Paragraph with 2-char first-line indent
    \\pagebreak                   Page break
    \\image{path}{width_in}       Image (width in inches, optional)
    \\begin{table}                Table start
    \\row                         New table row
    \\cell{Content}               Table cell (supports inline formatting)
    \\end{table}                  Table end

Format arguments (optional, comma-separated, order-independent):
    center | left | right | justify   Alignment
    <number>                          Font size in pt (e.g. 16)
    indent=<n>                        First-line indent in character widths
    font=<name>                       Font name (default: 微软雅黑)

    Examples:
        \\heading{Title}{center,16}
        \\para{text}{indent=2}
        \\para{text}{left,12,indent=2}

Inline formatting (inside \\para and \\cell, nestable):
    \\b{text}              Bold
    \\i{text}              Italic
    \\u{text}              Underline
    \\color{RRGGBB}{text}  Text color (hex RGB, e.g. FF0000 = red)

Lines starting with % are comments (ignored). Blank lines are ignored.
"""

import sys
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ALIGN_MAP = {
    "center": WD_ALIGN_PARAGRAPH.CENTER,
    "left": WD_ALIGN_PARAGRAPH.LEFT,
    "right": WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


# ──────────────────────────── DSL Parser ────────────────────────────


class DSLParser:
    """Parse LaTeX-like DSL code into a list of element descriptors."""

    def __init__(self, code: str):
        self.lines = code.split("\n")
        self.pos = 0
        self.elements: list[dict] = []

    # ── format-arg helpers ──

    @staticmethod
    def _parse_format_args(raw: str) -> dict:
        """Parse comma-separated format arguments.

        Recognised tokens (order-independent):
        - ``center`` / ``left`` / ``right`` / ``justify``  → alignment
        - bare integer/float                               → font size (pt)
        - ``indent=<n>``                                   → first-line indent
        - ``font=<name>``                                  → font name (default: 微软雅黑)
        """
        fmt: dict = {}
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if part in ALIGN_MAP:
                fmt["alignment"] = part
            elif part.startswith("indent="):
                fmt["indent"] = int(part.split("=", 1)[1])
            elif part.startswith("font="):
                fmt["font_name"] = part.split("=", 1)[1]
            else:
                try:
                    fmt["font_size_pt"] = float(part)
                except ValueError:
                    pass
        return fmt

    @staticmethod
    def _apply_format(paragraph, fmt: dict):
        """Apply parsed format dict to a python-docx paragraph."""
        font_name = fmt.get("font_name", "微软雅黑")
        for run in paragraph.runs:
            run.font.name = font_name
        if "alignment" in fmt:
            paragraph.alignment = ALIGN_MAP[fmt["alignment"]]
        if "font_size_pt" in fmt:
            size = Pt(fmt["font_size_pt"])
            for run in paragraph.runs:
                run.font.size = size
        if "indent" in fmt:
            # Estimate: assume ~12 pt per character width
            paragraph.paragraph_format.first_line_indent = Pt(
                fmt["indent"] * 12
            )

    # ── main parse loop ──

    def parse(self) -> list[dict]:
        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1

            if not line or line.startswith("%"):
                continue

            if line == r"\pagebreak":
                self.elements.append({"type": "pagebreak"})

            elif line.startswith(r"\heading{"):
                rest = line[len(r"\heading{"):]
                title, pos = self._match_brace(rest, 0)
                after = rest[pos + 1:]
                level = 1
                fmt: dict = {}
                if after.startswith("{"):
                    arg_str, p2 = self._match_brace(after, 1)
                    try:
                        level = int(arg_str)
                    except ValueError:
                        fmt = self._parse_format_args(arg_str)
                    else:
                        # level consumed; check for a format-args brace
                        after2 = after[p2 + 1:]
                        if after2.startswith("{"):
                            fmt_str, _ = self._match_brace(after2, 1)
                            fmt = self._parse_format_args(fmt_str)
                self.elements.append(
                    {"type": "heading", "text": title, "level": level, "format": fmt}
                )

            elif line.startswith(r"\para{"):
                rest = line[len(r"\para{"):]
                text, pos = self._match_brace(rest, 0)
                after = rest[pos + 1:]
                fmt = {}
                if after.startswith("{"):
                    fmt_str, _ = self._match_brace(after, 1)
                    fmt = self._parse_format_args(fmt_str)
                self.elements.append(
                    {"type": "paragraph", "text": text, "format": fmt}
                )

            elif line.startswith(r"\image{"):
                rest = line[len(r"\image{"):]
                path, pos = self._match_brace(rest, 0)
                after = rest[pos + 1:]
                width = 4.0
                if after.startswith("{"):
                    width_str, _ = self._match_brace(after, 1)
                    width = float(width_str)
                self.elements.append(
                    {"type": "image", "path": path, "width": width}
                )

            elif line == r"\begin{table}":
                self._parse_table()

        return self.elements

    def _parse_table(self):
        rows: list[list[str]] = []
        current_row: list[str] | None = None

        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()
            self.pos += 1

            if not line or line.startswith("%"):
                continue

            if line == r"\end{table}":
                break
            elif line == r"\row":
                if current_row is not None:
                    rows.append(current_row)
                current_row = []
            elif line.startswith(r"\cell{"):
                rest = line[len(r"\cell{"):]
                text, _ = self._match_brace(rest, 0)
                if current_row is not None:
                    current_row.append(text)

        if current_row is not None:
            rows.append(current_row)

        if rows:
            self.elements.append({"type": "table", "rows": rows})

    @staticmethod
    def _match_brace(text: str, start: int) -> tuple[str, int]:
        """Find matching ``}`` for an opening ``{`` implied at *start*.

        *start* is the index of the first character **after** the opening brace.
        Returns ``(content, position_of_closing_brace)``.
        """
        depth = 0
        i = start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                if depth == 0:
                    return text[start:i], i
                depth -= 1
            i += 1
        raise ValueError(f"Unmatched '{{' near position {start}")


# ──────────────────────── Inline formatter ─────────────────────────


class InlineFormatter:
    """Parse inline formatting tags and apply them to a python-docx paragraph.

    Supports ``\\b{}``, ``\\i{}``, ``\\u{}``, ``\\color{RRGGBB}{}`` with arbitrary nesting.
    """

    TAGS = {"b": "bold", "i": "italic", "u": "underline"}

    @classmethod
    def add_to(cls, paragraph, text: str):
        runs_data = cls._parse(text)
        for run_text, fmt in runs_data:
            run = paragraph.add_run(run_text)
            if fmt.get("bold"):
                run.bold = True
            if fmt.get("italic"):
                run.italic = True
            if fmt.get("underline"):
                run.underline = True
            if fmt.get("color"):
                run.font.color.rgb = RGBColor.from_string(fmt["color"])

    @classmethod
    def _parse(cls, text: str) -> list[tuple[str, dict]]:
        return cls._parse_segment(text, {})

    @classmethod
    def _parse_segment(cls, text: str, fmt: dict) -> list[tuple[str, dict]]:
        runs: list[tuple[str, dict]] = []
        pos = 0

        while pos < len(text):
            if text[pos] == "\\" and pos + 1 < len(text):
                tag_end = pos + 1
                while tag_end < len(text) and text[tag_end].isalpha():
                    tag_end += 1
                tag = text[pos + 1: tag_end]

                if tag == "color" and tag_end < len(text) and text[tag_end] == "{":
                    # \color{RRGGBB}{text} — two brace groups
                    color_end = cls._find_matching_brace(text, tag_end + 1)
                    color_val = text[tag_end + 1:color_end]
                    after_color = color_end + 1
                    if after_color < len(text) and text[after_color] == "{":
                        content_end = cls._find_matching_brace(text, after_color + 1)
                        inner = text[after_color + 1:content_end]
                        new_fmt = dict(fmt)
                        new_fmt["color"] = color_val
                        runs.extend(cls._parse_segment(inner, new_fmt))
                        pos = content_end + 1
                    else:
                        pos += 1
                elif tag in cls.TAGS and tag_end < len(text) and text[tag_end] == "{":
                    brace_start = tag_end + 1
                    brace_end = cls._find_matching_brace(text, brace_start)
                    inner = text[brace_start:brace_end]
                    new_fmt = dict(fmt)
                    new_fmt[cls.TAGS[tag]] = True
                    runs.extend(cls._parse_segment(inner, new_fmt))
                    pos = brace_end + 1
                else:
                    pos += 1
            else:
                plain_end = pos + 1
                while plain_end < len(text):
                    if text[plain_end] == "\\":
                        break
                    plain_end += 1
                runs.append((text[pos:plain_end], dict(fmt)))
                pos = plain_end

        return runs

    @staticmethod
    def _find_matching_brace(text: str, start: int) -> int:
        depth = 0
        i = start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                if depth == 0:
                    return i
                depth -= 1
            i += 1
        raise ValueError(f"Unmatched '{{' at position {start}")


# ──────────────────────── Document builder ─────────────────────────


class DocxBuilder:
    """Build a ``python-docx`` Document from parsed DSL elements."""

    def __init__(self, elements: list[dict]):
        self.elements = elements
        self.doc = Document()
        self._setup_page()

    def _setup_page(self):
        section = self.doc.sections[0]
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.25)

    def build(self) -> Document:
        for elem in self.elements:
            t = elem["type"]
            fmt = elem.get("format", {})

            if t == "heading":
                p = self.doc.add_paragraph()
                p.style = self.doc.styles[f"Heading {elem['level']}"]
                InlineFormatter.add_to(p, elem["text"])
                DSLParser._apply_format(p, fmt)

            elif t == "paragraph":
                p = self.doc.add_paragraph()
                InlineFormatter.add_to(p, elem["text"])
                DSLParser._apply_format(p, fmt)

            elif t == "table":
                self._build_table(elem["rows"])

            elif t == "image":
                self.doc.add_picture(
                    elem["path"], width=Inches(elem["width"])
                )

            elif t == "pagebreak":
                self.doc.add_page_break()

        return self.doc

    def _build_table(self, rows: list[list[str]]):
        if not rows:
            return

        num_cols = max(len(r) for r in rows)
        table = self.doc.add_table(rows=len(rows), cols=num_cols)
        table.style = "Table Grid"

        for i, row_data in enumerate(rows):
            for j, cell_text in enumerate(row_data):
                if j < num_cols:
                    cell = table.rows[i].cells[j]
                    p = cell.paragraphs[0]
                    InlineFormatter.add_to(p, cell_text)


# ──────────────────────────── Entry point ──────────────────────────


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python render.py <dsl_code> <output_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    dsl_code = sys.argv[1]
    output_path = Path(sys.argv[2])

    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        elements = DSLParser(dsl_code).parse()
        doc = DocxBuilder(elements).build()
        doc.save(str(output_path))
        print(f"Document saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
