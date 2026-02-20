"""Tests for Go backend codegen and parity with interpreter."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit_go import emit_go, get_runtime_path
from english_compiler.coreil.interp import run_coreil


def _has_go() -> bool:
    """Check if Go compiler is available."""
    return shutil.which("go") is not None


def _run_interp(doc: dict) -> str:
    """Run Core IL doc in interpreter, return stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_coreil(doc)
    assert rc == 0, f"Interpreter failed with exit code {rc}"
    return buf.getvalue()


def _run_go(doc: dict) -> str:
    """Compile and run Go code from Core IL doc, return stdout."""
    code, _ = emit_go(doc)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Write generated code
        go_file = tmppath / "main.go"
        go_file.write_text(code, encoding="utf-8")
        # Copy runtime
        runtime_src = get_runtime_path()
        shutil.copy(runtime_src, tmppath / "coreil_runtime.go")
        # Initialize Go module
        subprocess.run(
            ["go", "mod", "init", "coreil_test"],
            cwd=str(tmppath),
            capture_output=True,
            timeout=30,
        )
        # Build
        build_result = subprocess.run(
            ["go", "build", "-o", "test_prog", "."],
            cwd=str(tmppath),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert build_result.returncode == 0, f"Go build failed:\n{build_result.stderr}"
        # Run
        run_result = subprocess.run(
            [str(tmppath / "test_prog")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert run_result.returncode == 0, f"Go run failed:\n{run_result.stderr}"
        return run_result.stdout


def _lit(v) -> dict:
    return {"type": "Literal", "value": v}


def _var(n: str) -> dict:
    return {"type": "Var", "name": n}


def _bin(op: str, l: dict, r: dict) -> dict:
    return {"type": "Binary", "op": op, "left": l, "right": r}


def _prog(body: list[dict]) -> dict:
    return {"version": "coreil-1.9", "body": body}


# --- Codegen-only tests (no Go compiler needed) ---

def test_codegen_hello():
    """Basic codegen produces valid Go code."""
    doc = _prog([{"type": "Print", "args": [_lit("hello")]}])
    code, _ = emit_go(doc)
    assert "package main" in code
    assert "coreilPrint" in code
    assert "hello" in code


def test_codegen_function():
    """Function definition codegen."""
    doc = _prog([
        {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
            {"type": "Return", "value": _bin("+", _var("a"), _var("b"))},
        ]},
        {"type": "Print", "args": [{"type": "Call", "name": "add", "args": [_lit(2), _lit(3)]}]},
    ])
    code, _ = emit_go(doc)
    assert "func add(" in code
    assert "return" in code


def test_codegen_if_else():
    """If/else codegen."""
    doc = _prog([
        {"type": "If", "test": _lit(True),
         "then": [{"type": "Print", "args": [_lit("yes")]}],
         "else": [{"type": "Print", "args": [_lit("no")]}]},
    ])
    code, _ = emit_go(doc)
    assert "if isTruthy(" in code
    assert "} else {" in code


def test_codegen_while():
    """While loop codegen."""
    doc = _prog([
        {"type": "Let", "name": "i", "value": _lit(0)},
        {"type": "While", "test": _bin("<", _var("i"), _lit(3)), "body": [
            {"type": "Print", "args": [_var("i")]},
            {"type": "Assign", "name": "i", "value": _bin("+", _var("i"), _lit(1))},
        ]},
    ])
    code, _ = emit_go(doc)
    assert "for {" in code


def test_codegen_try_catch():
    """TryCatch codegen."""
    doc = _prog([
        {"type": "TryCatch", "body": [
            {"type": "Throw", "message": _lit("oops")},
        ], "catch_var": "e", "catch_body": [
            {"type": "Print", "args": [_var("e")]},
        ]},
    ])
    code, _ = emit_go(doc)
    assert "recover()" in code
    assert "panic(" in code


def test_codegen_for_range():
    """For loop with Range codegen."""
    doc = _prog([
        {"type": "For", "var": "i",
         "iter": {"type": "Range", "from": _lit(0), "to": _lit(3), "inclusive": False},
         "body": [{"type": "Print", "args": [_var("i")]}]},
    ])
    code, _ = emit_go(doc)
    assert "__from" in code
    assert "__to" in code


# --- Parity tests (require Go compiler) ---

def _check_parity(doc: dict) -> None:
    """Verify interpreter and Go backend produce identical output."""
    if not _has_go():
        return  # Skip if no Go compiler
    interp_out = _run_interp(doc)
    go_out = _run_go(doc)
    assert interp_out == go_out, f"Parity mismatch:\nInterpreter: {interp_out!r}\nGo: {go_out!r}"


def test_parity_hello():
    _check_parity(_prog([{"type": "Print", "args": [_lit("hello")]}]))


def test_parity_arithmetic():
    _check_parity(_prog([
        {"type": "Print", "args": [_bin("+", _lit(3), _lit(4))]},
        {"type": "Print", "args": [_bin("*", _lit(6), _lit(7))]},
    ]))


def test_parity_function():
    _check_parity(_prog([
        {"type": "FuncDef", "name": "square", "params": ["x"], "body": [
            {"type": "Return", "value": _bin("*", _var("x"), _var("x"))},
        ]},
        {"type": "Print", "args": [{"type": "Call", "name": "square", "args": [_lit(7)]}]},
    ]))


def test_parity_if_else():
    _check_parity(_prog([
        {"type": "Let", "name": "x", "value": _lit(10)},
        {"type": "If", "test": _bin(">", _var("x"), _lit(5)),
         "then": [{"type": "Print", "args": [_lit("big")]}],
         "else": [{"type": "Print", "args": [_lit("small")]}]},
    ]))


def test_parity_while():
    _check_parity(_prog([
        {"type": "Let", "name": "i", "value": _lit(0)},
        {"type": "While", "test": _bin("<", _var("i"), _lit(5)), "body": [
            {"type": "Assign", "name": "i", "value": _bin("+", _var("i"), _lit(1))},
        ]},
        {"type": "Print", "args": [_var("i")]},
    ]))


def test_parity_array():
    _check_parity(_prog([
        {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [_lit(1), _lit(2), _lit(3)]}},
        {"type": "Print", "args": [_var("arr")]},
        {"type": "Print", "args": [{"type": "Index", "base": _var("arr"), "index": _lit(1)}]},
        {"type": "Print", "args": [{"type": "Length", "base": _var("arr")}]},
    ]))


def test_parity_map():
    _check_parity(_prog([
        {"type": "Let", "name": "m", "value": {"type": "Map", "items": [
            {"key": _lit("a"), "value": _lit(1)},
            {"key": _lit("b"), "value": _lit(2)},
        ]}},
        {"type": "Print", "args": [{"type": "Get", "base": _var("m"), "key": _lit("a")}]},
    ]))


def test_parity_for_range():
    _check_parity(_prog([
        {"type": "Let", "name": "sum", "value": _lit(0)},
        {"type": "For", "var": "i",
         "iter": {"type": "Range", "from": _lit(1), "to": _lit(6), "inclusive": False},
         "body": [
             {"type": "Assign", "name": "sum", "value": _bin("+", _var("sum"), _var("i"))},
         ]},
        {"type": "Print", "args": [_var("sum")]},
    ]))


def test_parity_string_ops():
    _check_parity(_prog([
        {"type": "Let", "name": "s", "value": _lit("Hello World")},
        {"type": "Print", "args": [{"type": "StringUpper", "base": _var("s")}]},
        {"type": "Print", "args": [{"type": "StringLower", "base": _var("s")}]},
    ]))


def test_parity_try_catch():
    _check_parity(_prog([
        {"type": "TryCatch", "body": [
            {"type": "Throw", "message": _lit("test error")},
        ], "catch_var": "e", "catch_body": [
            {"type": "Print", "args": [_var("e")]},
        ]},
    ]))


def test_parity_break_continue():
    _check_parity(_prog([
        {"type": "Let", "name": "result", "value": _lit(0)},
        {"type": "For", "var": "i",
         "iter": {"type": "Range", "from": _lit(0), "to": _lit(10), "inclusive": False},
         "body": [
             {"type": "If", "test": _bin("==", _bin("%", _var("i"), _lit(2)), _lit(0)),
              "then": [{"type": "Continue"}]},
             {"type": "If", "test": _bin(">=", _var("i"), _lit(7)),
              "then": [{"type": "Break"}]},
             {"type": "Assign", "name": "result", "value": _bin("+", _var("result"), _var("i"))},
         ]},
        {"type": "Print", "args": [_var("result")]},
    ]))


def test_parity_type_convert():
    _check_parity(_prog([
        {"type": "Print", "args": [{"type": "ToInt", "value": _lit(3.7)}]},
        {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(5)}]},
        {"type": "Print", "args": [{"type": "ToString", "value": _lit(123)}]},
    ]))


# --- JSON tests ---

def test_codegen_json_parse():
    """JsonParse codegen produces valid Go code."""
    doc = _prog([
        {"type": "Let", "name": "data", "value": {"type": "JsonParse", "source": _lit('{"a": 1}')}},
        {"type": "Print", "args": [_var("data")]},
    ])
    code, _ = emit_go(doc)
    assert "jsonParse" in code


def test_codegen_json_stringify():
    """JsonStringify codegen produces valid Go code."""
    doc = _prog([
        {"type": "Let", "name": "m", "value": {"type": "Map", "items": [
            {"key": _lit("x"), "value": _lit(1)},
        ]}},
        {"type": "Print", "args": [{"type": "JsonStringify", "value": _var("m")}]},
    ])
    code, _ = emit_go(doc)
    assert "jsonStringify" in code


def test_parity_json_parse():
    """Parse JSON object and access fields."""
    _check_parity(_prog([
        {"type": "Let", "name": "data", "value": {"type": "JsonParse", "source": _lit('{"name": "Alice", "age": 30}')}},
        {"type": "Print", "args": [{"type": "Get", "base": _var("data"), "key": _lit("name")}]},
        {"type": "Print", "args": [{"type": "Get", "base": _var("data"), "key": _lit("age")}]},
    ]))


def test_parity_json_parse_array():
    """Parse JSON array."""
    _check_parity(_prog([
        {"type": "Let", "name": "arr", "value": {"type": "JsonParse", "source": _lit('[1, 2, 3]')}},
        {"type": "Print", "args": [{"type": "Length", "base": _var("arr")}]},
        {"type": "Print", "args": [{"type": "Index", "base": _var("arr"), "index": _lit(0)}]},
    ]))


def test_parity_json_stringify():
    """Stringify a map to JSON."""
    _check_parity(_prog([
        {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [_lit(1), _lit(2), _lit(3)]}},
        {"type": "Print", "args": [{"type": "JsonStringify", "value": _var("arr")}]},
    ]))


# --- Regex tests ---

def test_codegen_regex_match():
    """RegexMatch codegen produces valid Go code."""
    doc = _prog([
        {"type": "Print", "args": [{"type": "RegexMatch", "string": _lit("hello"), "pattern": _lit("hel+")}]},
    ])
    code, _ = emit_go(doc)
    assert "regexMatch" in code


def test_parity_regex_match():
    """Regex match returns boolean."""
    _check_parity(_prog([
        {"type": "Print", "args": [{"type": "RegexMatch", "string": _lit("hello world"), "pattern": _lit("world")}]},
        {"type": "Print", "args": [{"type": "RegexMatch", "string": _lit("hello world"), "pattern": _lit("xyz")}]},
    ]))


def test_parity_regex_find_all():
    """Regex find all matches."""
    _check_parity(_prog([
        {"type": "Let", "name": "matches", "value": {"type": "RegexFindAll", "string": _lit("cat bat hat"), "pattern": _lit("[cbh]at")}},
        {"type": "Print", "args": [_var("matches")]},
    ]))


def test_parity_regex_replace():
    """Regex replace all occurrences."""
    _check_parity(_prog([
        {"type": "Print", "args": [{"type": "RegexReplace", "string": _lit("foo123bar456"), "pattern": _lit("[0-9]+"), "replacement": _lit("#")}]},
    ]))


def test_parity_regex_split():
    """Regex split string."""
    _check_parity(_prog([
        {"type": "Let", "name": "parts", "value": {"type": "RegexSplit", "string": _lit("one,two;three four"), "pattern": _lit("[,; ]")}},
        {"type": "Print", "args": [_var("parts")]},
    ]))


def main() -> None:
    tests = [
        # Codegen-only
        test_codegen_hello,
        test_codegen_function,
        test_codegen_if_else,
        test_codegen_while,
        test_codegen_try_catch,
        test_codegen_for_range,
        test_codegen_json_parse,
        test_codegen_json_stringify,
        test_codegen_regex_match,
        # Parity
        test_parity_hello,
        test_parity_arithmetic,
        test_parity_function,
        test_parity_if_else,
        test_parity_while,
        test_parity_array,
        test_parity_map,
        test_parity_for_range,
        test_parity_string_ops,
        test_parity_try_catch,
        test_parity_break_continue,
        test_parity_type_convert,
        test_parity_json_parse,
        test_parity_json_parse_array,
        test_parity_json_stringify,
        test_parity_regex_match,
        test_parity_regex_find_all,
        test_parity_regex_replace,
        test_parity_regex_split,
    ]

    has_go = _has_go()
    print(f"Go compiler available: {has_go}")
    print("Running Go backend tests...\n")

    for test in tests:
        test()
        print(f"  {test.__name__}: pass")

    print(f"\nAll {len(tests)} Go backend tests passed!")


if __name__ == "__main__":
    main()
