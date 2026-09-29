---
name: docx
description: "Create or edit Word documents (.docx files). Use When the user wants to create a new Word document (report, memo, letter, etc.) or edit an existing .docx file (add comments, accept tracked changes, modify content). DO NOT Use When working with PDFs, spreadsheets, or when no Word document is involved."
---

# DOCX creation OR editing

Choose your approach by task:

| Task | Approach |
|---|---|
| **Create** a new document | Pass LaTeX-like DSL code to `render.py` via `run_script` |
| **Edit** an existing document | Read as DSL → modify → re-render via `render.py`, or use XML helper scripts |

**NOTE:** You should choose only one Approach, do not choose both!

> Script paths below are relative to this skill's directory.

## Creating documents

### DSL syntax

```
\heading{Title}              H1 heading
\heading{Title}{2}           H2 heading (level 0-9)
\heading{Title}{center,16}   H1 with alignment + font size (pt)
\para{Body text}             Paragraph
\para{text}{indent=2}        Paragraph with 2-char first-line indent
\pagebreak                   Page break
\image{path}{width_in}       Image (width in inches, optional)
\begin{table}                Table start
\row                         New table row
\cell{Content}               Table cell (supports inline formatting)
\end{table}                  Table end
```

**Format arguments** (optional, comma-separated, order-independent, on `\heading` and `\para`):

| Token | Effect |
|---|---|
| `center` / `left` / `right` / `justify` | Paragraph alignment |
| `<number>` | Font size in pt (e.g. `16` for 三号) |
| `indent=<n>` | First-line indent in character widths |
| `font=<name>` | Font name (default: 微软雅黑) |

Examples: `\heading{Title}{center,16}`, `\para{text}{indent=2}`, `\para{text}{left,12,indent=2}`

**Inline formatting** (inside `\para` and `\cell`, nestable):

```
\b{bold text}
\i{italic text}
\u{underline text}
\color{FF0000}{red text}          hex RGB color
\b{bold \color{0000FF}{blue}}    nesting example
```

Lines starting with `%` are comments (ignored). Blank lines are ignored.

### Workflow

Call `run_script` with the complete DSL code and output path:

```
action: run_script
arguments:
  skill_name: "docx"
  script_name: "render.py"
  script_args: ["<dsl_code>", "<output_path>"]
```

- `script_args[0]`: the complete DSL code as a single string
- `script_args[1]`: output `.docx` path (relative to project root, or absolute)

**Example** — create a report with heading, paragraph, and table:

```
action: run_script
arguments:
  skill_name: "docx"
  script_name: "render.py"
  script_args: [
    "\\heading{Quarterly Report}\n\\para{Here is the summary.}\n\\begin{table}\n\\row\n\\cell{\\b{Name}}\n\\cell{\\b{Score}}\n\\row\n\\cell{Alice}\n\\cell{95}\n\\end{table}",
    "report.docx"
  ]
```

**Notes:**

- Default page size is A4 (8.27 × 11.69 inches), margins 1 inch top/bottom, 1.25 inch left/right.
- Images require an absolute file path.
- Tables use the "Table Grid" style (bordered).
- `\n` in the DSL code string separates lines. Each command must be on its own line.
- If the DSL code is very long and exceeds command-line limits, write it to a temporary `.txt` file first, then read the file content and pass it.

Then finish the workflow.

**Do Not Repeat using this workflow！**

> **Note:** After completing this operation, no additional verification is needed unless the user explicitly requests it.

## Editing via DSL (read → modify → render)

To update an existing document's content while preserving formatting:

1. Call `read_docx.py` to get the format-aware DSL code of an existing document:

```
action: run_script
arguments:
  skill_name: "docx"
  script_name: "read_docx.py"
  script_args: ["<input_docx>"]
```

The output captures headings, paragraphs, inline formatting (bold/italic/underline/color), alignment, font size, indent, page breaks, and tables. This output can be passed directly to `render.py` to regenerate the document.

> **Note:** Images are not extracted — they appear as `% [Image]` comments in the output. When re-rendering, images will be lost.

2. Modify the DSL code as needed
3. Call `render.py` with the updated DSL, using the same file path to overwrite the original

```
action: run_script
arguments:
  skill_name: "docx"
  script_name: "render.py"
  script_args: ["<updated_dsl_code>", "<original_docx_path>"]
```

> **Warning:** This replaces the entire document. Images and elements not captured by `read_docx.py` will be lost.

Then finish the workflow.

**Do Not Repeat using this workflow！**

> **Note:** After completing this operation, no additional verification is needed unless the user explicitly requests it.

## Dependencies

| Dependency | Type | Used for |
|---|---|---|
| `python-docx` | Python package (`pip install python-docx`) | Creating documents via `render.py` and reading via `read_docx.py` |
| `defusedxml` | Python package (`pip install defusedxml`) | XML parsing in editing scripts |
| `lxml` | Python package (`pip install lxml`) | XSD schema validation |

If any dependency is missing, inform the user of the complete dependency list above and ask them to install the missing one. Do NOT attempt to install dependencies yourself.
