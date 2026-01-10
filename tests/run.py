"""Minimal test runner for Core IL examples."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil


def _run_example(path: Path, expected_output: str) -> None:
    doc = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed for {path}: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0, f"Interpreter failed for {path}"

    output = buffer.getvalue()
    assert output == expected_output, (
        f"Output mismatch for {path}: expected {expected_output!r}, got {output!r}"
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    examples = root / "examples"

    _run_example(examples / "hello.coreil.json", "hello\n")
    _run_example(examples / "math.coreil.json", "49\n")
    _run_example(examples / "if.coreil.json", "even\n")
    _run_example(examples / "array_index.coreil.json", "4\n")
    _run_example(examples / "array_setindex.coreil.json", "99\n")
    _run_example(examples / "array_length.coreil.json", "3\n")
    _run_example(examples / "bubble_sort.coreil.json", "[1, 2, 3, 4, 5, 6, 7]\n")

    print("All tests passed.")


if __name__ == "__main__":
    main()
