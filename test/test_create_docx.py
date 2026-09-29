"""Test docx SKILL: render a document via render.py DSL.

Creates test/test.docx with:
  - Title "Test": 三号 (16pt), centered, bold, red
  - Body "This is a test.": first-line indent 2 characters
"""

import subprocess
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RENDER_SCRIPT = PROJECT_ROOT / "skills" / "docx"  / "render.py"
OUTPUT_PATH = Path(__file__).resolve().parent / "test.docx"

# DSL code:
#   \heading{\b{\color{FF0000}{Test}}}{center,16}  →  H1, centered, 16pt (三号), bold + red
#   \para{This is a test.}{indent=2}  →  first-line indent 2 chars
DSL_CODE = r"""\heading{\b{\color{FF0000}{Test}}}{center,16}
\para{This is a test.}{indent=2}"""


def main():
    result = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT), DSL_CODE, str(OUTPUT_PATH)],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)

    # Verify the output
    if OUTPUT_PATH.exists():
        print(f"OK: {OUTPUT_PATH} created ({OUTPUT_PATH.stat().st_size} bytes)")
    else:
        print("FAIL: output file not created", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
