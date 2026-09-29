"""Test docx SKILL: read_docx.py reads a .docx and outputs DSL code.

Tests:
  1. Read an existing docx (test_cua.docx) and verify DSL output
  2. Round-trip: render → read → verify DSL contains expected elements
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
READ_SCRIPT = PROJECT_ROOT / "skills" / "docx" / "read_docx.py"
RENDER_SCRIPT = PROJECT_ROOT / "skills" / "docx" / "render.py"
TEST_DIR = Path(__file__).resolve().parent


def run_read(docx_path: Path) -> str:
    """Call read_docx.py and return its stdout."""
    result = subprocess.run(
        [sys.executable, str(READ_SCRIPT), str(docx_path)],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"FAIL: read_docx.py exited with code {result.returncode}", file=sys.stderr)
        print(result.stderr.decode('utf-8', errors='replace'), file=sys.stderr)
        sys.exit(1)
    return result.stdout.decode('utf-8', errors='replace').strip()


def run_render(dsl_code: str, output_path: Path):
    """Call render.py to create a docx from DSL code."""
    result = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT), dsl_code, str(output_path)],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
    )
    if result.returncode != 0:
        print(f"FAIL: render.py exited with code {result.returncode}", file=sys.stderr)
        print(result.stderr.decode('utf-8', errors='replace'), file=sys.stderr)
        sys.exit(1)


def test_read_existing_docx():
    """Test 1: Read the existing test_cua.docx and verify DSL output."""
    docx_path = TEST_DIR / "test_cua.docx"
    if not docx_path.exists():
        print(f"SKIP: {docx_path} not found")
        return

    print("=== Test 1: Read existing test_cua.docx ===")
    dsl = run_read(docx_path)
    print(dsl)
    print()

    # Verify basic structure
    assert r"\heading{" in dsl, "FAIL: no \\heading found in DSL output"
    assert r"\para{" in dsl, "FAIL: no \\para found in DSL output"
    print("PASS: DSL contains \\heading and \\para")


def test_roundtrip():
    """Test 2: Render a docx, read it back, verify DSL consistency."""
    print("=== Test 2: Round-trip render → read ===")

    dsl_input = (
        r"\heading{Round Trip Test}{center,16}" + "\n"
        r"\para{\b{Bold text} and \color{FF0000}{red text}}{12,indent=2}"
    )

    output_path = TEST_DIR / "test_roundtrip.docx"

    # Step 1: Render
    run_render(dsl_input, output_path)
    assert output_path.exists(), "FAIL: render did not create output file"
    print(f"  Rendered: {output_path} ({output_path.stat().st_size} bytes)")

    # Step 2: Read back
    dsl_output = run_read(output_path)
    print(f"  Read back DSL:\n{dsl_output}")
    print()

    # Step 3: Verify
    assert r"\heading{" in dsl_output, "FAIL: no \\heading in round-trip output"
    assert "Round Trip Test" in dsl_output, "FAIL: heading text missing"
    assert r"\para{" in dsl_output, "FAIL: no \\para in round-trip output"
    assert r"\b{" in dsl_output, "FAIL: bold formatting lost"
    assert r"\color{FF0000}{" in dsl_output, "FAIL: color formatting lost"
    assert "indent=2" in dsl_output, "FAIL: indent format arg lost"
    print("PASS: round-trip preserves heading, paragraph, bold, color, indent")

    # Cleanup
    output_path.unlink()


def test_read_nonexistent():
    """Test 3: Read a non-existent file should fail gracefully."""
    print("=== Test 3: Read non-existent file ===")
    result = subprocess.run(
        [sys.executable, str(READ_SCRIPT), "nonexistent.docx"],
        capture_output=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode != 0, "FAIL: should have exited with non-zero code"
    print("PASS: non-existent file handled correctly")


def main():
    test_read_existing_docx()
    test_roundtrip()
    test_read_nonexistent()
    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
