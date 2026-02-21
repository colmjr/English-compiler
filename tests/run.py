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
    _run_example(examples / "fn_add.coreil.json", "5\n")
    _run_example(examples / "for_sum.coreil.json", "15\n")
    _run_example(examples / "foreach_print.coreil.json", "1\n2\n3\n")
    _run_example(examples / "map_demo.coreil.json", "2\n")
    _run_example(examples / "heap_demo.coreil.json", "size: 3\npeek: one\npopped: one\npopped: three\npopped: five\n")
    _run_example(examples / "heap_kth_smallest.coreil.json", "3rd smallest: 4\n")
    _run_example(examples / "math_basic.coreil.json", "0.8414709848078965\n3.0\n3.141592653589793\n")
    _run_example(examples / "json_basic.coreil.json", "test\n42\n[1, 2, 3]\n")
    _run_example(examples / "regex_basic.coreil.json", "has digits: True\nfound digits: ['123', '456']\nreplaced: Hello NUM World NUM\nsplit: ['a', 'b', 'c', 'd']\n")
    _run_example(examples / "string_ops.coreil.json", "Hello World\nHELLO\nworld\n['a', 'b', 'c']\nTrue\nTrue\nTrue\nbaz bar baz\n")
    _run_example(examples / "slice_test.coreil.json", "[2, 3, 4]\n[1, 2]\n[4, 5]\n")
    _run_example(examples / "slice_negative.coreil.json", "[4, 5]\n[1, 2, 3, 4]\n[2, 3, 4]\n")
    _run_example(examples / "array_negative_index.coreil.json", "5\n4\n1\n[1, 2, 3, 4, 99]\nc\n")
    _run_example(examples / "type_convert.coreil.json", "3\n42\n5.0\n3.14\n123\nTrue\n")
    _run_example(examples / "ternary.coreil.json", "big\nno\n")
    _run_example(examples / "string_format.coreil.json", "Hello, World!\nThe answer is 42\n")

    print("All tests passed.")


if __name__ == "__main__":
    main()
