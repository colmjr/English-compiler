"""Rust backend tests.

Tests Rust code generation in english_compiler/coreil/emit_rust.py.
If rustc is not available, tests verify that emit_rust() produces non-empty
code without errors (codegen-only mode).

Run with: python -m tests.test_rust
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit_rust import emit_rust, get_runtime_path
from english_compiler.coreil.interp import run_coreil


_RUST_AVAILABLE = shutil.which("rustc") is not None


def _run_rust(code: str) -> str:
    """Compile and execute Rust code, returning stdout."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write source
        src_path = tmp_path / "program.rs"
        src_path.write_text(code, encoding="utf-8")

        # Copy runtime
        runtime_src = get_runtime_path()
        runtime_dst = tmp_path / "coreil_runtime.rs"
        shutil.copy(runtime_src, runtime_dst)

        # Compile
        exe_path = tmp_path / "program"
        result = subprocess.run(
            ["rustc", "--edition", "2021", str(src_path), "-o", str(exe_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Rust compilation failed:\n{result.stderr}")

        # Run
        result = subprocess.run(
            [str(exe_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Rust execution failed:\n{result.stderr}")
        return result.stdout


def _run_interp(doc: dict) -> str:
    """Run Core IL interpreter and return stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        run_coreil(doc)
    return buf.getvalue()


def _test_parity(doc: dict, test_name: str) -> None:
    """Test that interpreter and Rust produce identical output."""
    interp_output = _run_interp(doc)
    rust_code = emit_rust(doc)
    assert rust_code.strip(), f"{test_name}: emit_rust() produced empty code"

    if _RUST_AVAILABLE:
        rust_output = _run_rust(rust_code)
        if interp_output != rust_output:
            print(f"FAILED: {test_name}")
            print(f"  Interpreter: {interp_output!r}")
            print(f"  Rust:        {rust_output!r}")
            raise AssertionError(f"Output mismatch in {test_name}")
    print(f"  {test_name}: \u2713" + ("" if _RUST_AVAILABLE else " (codegen only)"))


def test_literals():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Print", "args": [{"type": "Literal", "value": 42}]},
            {"type": "Print", "args": [{"type": "Literal", "value": 3.14}]},
            {"type": "Print", "args": [{"type": "Literal", "value": "hello"}]},
            {"type": "Print", "args": [{"type": "Literal", "value": True}]},
            {"type": "Print", "args": [{"type": "Literal", "value": False}]},
            {"type": "Print", "args": [{"type": "Literal", "value": None}]},
        ],
    }
    _test_parity(doc, "literals")


def test_arithmetic():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Print", "args": [{"type": "Binary", "op": "+", "left": {"type": "Literal", "value": 10}, "right": {"type": "Literal", "value": 3}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": "-", "left": {"type": "Literal", "value": 10}, "right": {"type": "Literal", "value": 3}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": "*", "left": {"type": "Literal", "value": 10}, "right": {"type": "Literal", "value": 3}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": "%", "left": {"type": "Literal", "value": 10}, "right": {"type": "Literal", "value": 3}}]},
        ],
    }
    _test_parity(doc, "arithmetic")


def test_comparison():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Print", "args": [{"type": "Binary", "op": "==", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 1}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": "!=", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 2}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": "<", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 2}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": ">", "left": {"type": "Literal", "value": 2}, "right": {"type": "Literal", "value": 1}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": "<=", "left": {"type": "Literal", "value": 1}, "right": {"type": "Literal", "value": 1}}]},
            {"type": "Print", "args": [{"type": "Binary", "op": ">=", "left": {"type": "Literal", "value": 2}, "right": {"type": "Literal", "value": 2}}]},
        ],
    }
    _test_parity(doc, "comparison")


def test_arrays():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [
                {"type": "Literal", "value": 10},
                {"type": "Literal", "value": 20},
                {"type": "Literal", "value": 30},
            ]}},
            {"type": "Print", "args": [{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": 0}}]},
            {"type": "Print", "args": [{"type": "Length", "base": {"type": "Var", "name": "arr"}}]},
            {"type": "Push", "base": {"type": "Var", "name": "arr"}, "value": {"type": "Literal", "value": 40}},
            {"type": "Print", "args": [{"type": "Length", "base": {"type": "Var", "name": "arr"}}]},
        ],
    }
    _test_parity(doc, "arrays")


def test_maps():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Let", "name": "m", "value": {"type": "Map", "items": [
                {"key": {"type": "Literal", "value": "a"}, "value": {"type": "Literal", "value": 1}},
                {"key": {"type": "Literal", "value": "b"}, "value": {"type": "Literal", "value": 2}},
            ]}},
            {"type": "Print", "args": [{"type": "Get", "base": {"type": "Var", "name": "m"}, "key": {"type": "Literal", "value": "a"}}]},
            {"type": "Print", "args": [{"type": "GetDefault", "base": {"type": "Var", "name": "m"}, "key": {"type": "Literal", "value": "c"}, "default": {"type": "Literal", "value": 99}}]},
            {"type": "Set", "base": {"type": "Var", "name": "m"}, "key": {"type": "Literal", "value": "c"}, "value": {"type": "Literal", "value": 3}},
            {"type": "Print", "args": [{"type": "Get", "base": {"type": "Var", "name": "m"}, "key": {"type": "Literal", "value": "c"}}]},
        ],
    }
    _test_parity(doc, "maps")


def test_if_else():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "If",
             "test": {"type": "Binary", "op": ">", "left": {"type": "Literal", "value": 5}, "right": {"type": "Literal", "value": 3}},
             "then": [{"type": "Print", "args": [{"type": "Literal", "value": "yes"}]}],
             "else": [{"type": "Print", "args": [{"type": "Literal", "value": "no"}]}]},
            {"type": "If",
             "test": {"type": "Binary", "op": "<", "left": {"type": "Literal", "value": 5}, "right": {"type": "Literal", "value": 3}},
             "then": [{"type": "Print", "args": [{"type": "Literal", "value": "yes"}]}],
             "else": [{"type": "Print", "args": [{"type": "Literal", "value": "no"}]}]},
        ],
    }
    _test_parity(doc, "if_else")


def test_while_loop():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Let", "name": "i", "value": {"type": "Literal", "value": 0}},
            {"type": "While",
             "test": {"type": "Binary", "op": "<", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 3}},
             "body": [
                 {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
                 {"type": "Assign", "name": "i", "value": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}}},
             ]},
        ],
    }
    _test_parity(doc, "while_loop")


def test_for_range():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "For", "var": "i",
             "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 4}, "inclusive": False},
             "body": [
                 {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
             ]},
        ],
    }
    _test_parity(doc, "for_range")


def test_for_each():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [
                {"type": "Literal", "value": "a"},
                {"type": "Literal", "value": "b"},
                {"type": "Literal", "value": "c"},
            ]}},
            {"type": "ForEach", "var": "x", "iter": {"type": "Var", "name": "arr"},
             "body": [
                 {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
             ]},
        ],
    }
    _test_parity(doc, "for_each")


def test_functions():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "FuncDef", "name": "double", "params": ["x"], "body": [
                {"type": "Return", "value": {"type": "Binary", "op": "*", "left": {"type": "Var", "name": "x"}, "right": {"type": "Literal", "value": 2}}},
            ]},
            {"type": "Print", "args": [{"type": "Call", "name": "double", "args": [{"type": "Literal", "value": 21}]}]},
        ],
    }
    _test_parity(doc, "functions")


def test_string_ops():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "Print", "args": [{"type": "StringLength", "base": {"type": "Literal", "value": "hello"}}]},
            {"type": "Print", "args": [{"type": "StringUpper", "base": {"type": "Literal", "value": "hello"}}]},
            {"type": "Print", "args": [{"type": "StringTrim", "base": {"type": "Literal", "value": "  hi  "}}]},
            {"type": "Print", "args": [{"type": "StringLower", "base": {"type": "Literal", "value": "WORLD"}}]},
        ],
    }
    _test_parity(doc, "string_ops")


def test_break_continue():
    doc = {
        "version": "coreil-1.8",
        "body": [
            # Print even numbers 0-8 using continue, break at 10
            {"type": "Let", "name": "i", "value": {"type": "Literal", "value": 0}},
            {"type": "While", "test": {"type": "Literal", "value": True}, "body": [
                {"type": "If",
                 "test": {"type": "Binary", "op": ">=", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 10}},
                 "then": [{"type": "Break"}]},
                {"type": "Let", "name": "cur", "value": {"type": "Var", "name": "i"}},
                {"type": "Assign", "name": "i", "value": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}}},
                {"type": "If",
                 "test": {"type": "Binary", "op": "!=",
                          "left": {"type": "Binary", "op": "%", "left": {"type": "Var", "name": "cur"}, "right": {"type": "Literal", "value": 2}},
                          "right": {"type": "Literal", "value": 0}},
                 "then": [{"type": "Continue"}]},
                {"type": "Print", "args": [{"type": "Var", "name": "cur"}]},
            ]},
        ],
    }
    _test_parity(doc, "break_continue")


def test_try_catch():
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "TryCatch",
             "body": [
                 {"type": "Print", "args": [{"type": "Literal", "value": "before throw"}]},
                 {"type": "Throw", "message": {"type": "Literal", "value": "oops"}},
                 {"type": "Print", "args": [{"type": "Literal", "value": "after throw"}]},
             ],
             "catch_var": "e",
             "catch_body": [
                 {"type": "Print", "args": [{"type": "Literal", "value": "caught"}]},
             ]},
        ],
    }
    _test_parity(doc, "try_catch")


def test_try_catch_finally():
    """Finally block must execute even when catch body throws."""
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "TryCatch",
             "body": [
                 {"type": "Print", "args": [{"type": "Literal", "value": "try"}]},
                 {"type": "Throw", "message": {"type": "Literal", "value": "err1"}},
             ],
             "catch_var": "e",
             "catch_body": [
                 {"type": "Print", "args": [{"type": "Literal", "value": "catch"}]},
             ],
             "finally_body": [
                 {"type": "Print", "args": [{"type": "Literal", "value": "finally"}]},
             ]},
        ],
    }
    _test_parity(doc, "try_catch_finally")


def test_try_catch_finally_rethrow():
    """Finally block must execute even when catch body throws, then re-panic."""
    doc = {
        "version": "coreil-1.8",
        "body": [
            {"type": "TryCatch",
             "body": [
                 # Outer try-catch to capture the re-thrown panic
                 {"type": "TryCatch",
                  "body": [
                      {"type": "Throw", "message": {"type": "Literal", "value": "inner"}},
                  ],
                  "catch_var": "e1",
                  "catch_body": [
                      {"type": "Print", "args": [{"type": "Literal", "value": "catch1"}]},
                      {"type": "Throw", "message": {"type": "Literal", "value": "from catch"}},
                  ],
                  "finally_body": [
                      {"type": "Print", "args": [{"type": "Literal", "value": "finally1"}]},
                  ]},
             ],
             "catch_var": "e2",
             "catch_body": [
                 {"type": "Print", "args": [{"type": "Binary", "op": "+",
                  "left": {"type": "Literal", "value": "outer caught: "},
                  "right": {"type": "Var", "name": "e2"}}]},
             ]},
        ],
    }
    _test_parity(doc, "try_catch_finally_rethrow")


def main() -> int:
    mode = "full parity" if _RUST_AVAILABLE else "codegen-only (rustc not found)"
    print(f"Running Rust backend tests ({mode})...\n")

    tests = [
        test_literals,
        test_arithmetic,
        test_comparison,
        test_arrays,
        test_maps,
        test_if_else,
        test_while_loop,
        test_for_range,
        test_for_each,
        test_functions,
        test_string_ops,
        test_break_continue,
        test_try_catch,
        test_try_catch_finally,
        test_try_catch_finally_rethrow,
    ]

    failures = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            failures.append(str(e))
        except Exception as e:
            failures.append(f"{test.__name__}: {e}")
            print(f"  {test.__name__}: \u2717 ({e})")

    print()
    if failures:
        print(f"{len(failures)}/{len(tests)} tests failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(tests)} Rust backend tests passed! \u2713")
    return 0


if __name__ == "__main__":
    sys.exit(main())
