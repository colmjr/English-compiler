"""Tests for the Core IL optimization pass."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.optimize import optimize


def _run_and_capture(doc: dict) -> str:
    """Run a Core IL program and capture stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = run_coreil(doc)
    assert rc == 0, f"Interpreter failed with exit code {rc}"
    return buf.getvalue()


def _make_program(body: list[dict], version: str = "coreil-1.9") -> dict:
    return {"version": version, "body": body}


def _lit(value) -> dict:
    return {"type": "Literal", "value": value}


def _var(name: str) -> dict:
    return {"type": "Var", "name": name}


def _binary(op: str, left: dict, right: dict) -> dict:
    return {"type": "Binary", "op": op, "left": left, "right": right}


def test_constant_folding_arithmetic():
    """3 + 4 should fold to 7."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary("+", _lit(3), _lit(4))},
        {"type": "Print", "args": [_var("x")]},
    ])
    optimized = optimize(prog)
    # Check that the expression was folded
    let_stmt = optimized["body"][0]
    assert let_stmt["value"] == {"type": "Literal", "value": 7}
    # Verify same output
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_constant_folding_string_concat():
    """'hello' + ' world' should fold to 'hello world'."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary("+", _lit("hello"), _lit(" world"))},
        {"type": "Print", "args": [_var("x")]},
    ])
    optimized = optimize(prog)
    let_stmt = optimized["body"][0]
    assert let_stmt["value"] == {"type": "Literal", "value": "hello world"}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_constant_folding_comparison():
    """3 < 5 should fold to True."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary("<", _lit(3), _lit(5))},
        {"type": "Print", "args": [_var("x")]},
    ])
    optimized = optimize(prog)
    let_stmt = optimized["body"][0]
    assert let_stmt["value"] == {"type": "Literal", "value": True}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_no_fold_division_by_zero():
    """5 // 0 should NOT be folded (would cause runtime error)."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary("//", _lit(5), _lit(0))},
    ])
    optimized = optimize(prog)
    let_stmt = optimized["body"][0]
    # Should still be a Binary node, not folded
    assert let_stmt["value"]["type"] == "Binary"


def test_dead_code_after_return():
    """Statements after Return should be removed."""
    prog = _make_program([
        {"type": "FuncDef", "name": "f", "params": [], "body": [
            {"type": "Return", "value": _lit(42)},
            {"type": "Print", "args": [_lit("unreachable")]},
        ]},
        {"type": "Print", "args": [{"type": "Call", "name": "f", "args": []}]},
    ])
    optimized = optimize(prog)
    func_body = optimized["body"][0]["body"]
    assert len(func_body) == 1  # Only Return, Print removed
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_dead_code_after_break():
    """Statements after Break should be removed."""
    prog = _make_program([
        {"type": "Let", "name": "i", "value": _lit(0)},
        {"type": "While", "test": _lit(True), "body": [
            {"type": "Break"},
            {"type": "Print", "args": [_lit("unreachable")]},
        ]},
        {"type": "Print", "args": [_lit("done")]},
    ])
    optimized = optimize(prog)
    while_body = optimized["body"][1]["body"]
    assert len(while_body) == 1  # Only Break
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_identity_add_zero():
    """x + 0 should simplify to x."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _lit(42)},
        {"type": "Let", "name": "y", "value": _binary("+", _var("x"), _lit(0))},
        {"type": "Print", "args": [_var("y")]},
    ])
    optimized = optimize(prog)
    let_y = optimized["body"][1]
    assert let_y["value"] == {"type": "Var", "name": "x"}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_identity_multiply_one():
    """x * 1 should simplify to x."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _lit(7)},
        {"type": "Let", "name": "y", "value": _binary("*", _var("x"), _lit(1))},
        {"type": "Print", "args": [_var("y")]},
    ])
    optimized = optimize(prog)
    let_y = optimized["body"][1]
    assert let_y["value"] == {"type": "Var", "name": "x"}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_identity_and_true():
    """x and true should simplify to x."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _lit(True)},
        {"type": "Let", "name": "y", "value": _binary("and", _var("x"), _lit(True))},
        {"type": "Print", "args": [_var("y")]},
    ])
    optimized = optimize(prog)
    let_y = optimized["body"][1]
    assert let_y["value"] == {"type": "Var", "name": "x"}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_not_folding():
    """not true should fold to false."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": {"type": "Not", "arg": _lit(True)}},
        {"type": "Print", "args": [_var("x")]},
    ])
    optimized = optimize(prog)
    let_x = optimized["body"][0]
    assert let_x["value"] == {"type": "Literal", "value": False}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_does_not_mutate_input():
    """Optimizer should not mutate the input program."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary("+", _lit(1), _lit(2))},
        {"type": "Print", "args": [_var("x")]},
    ])
    original = json.dumps(prog, sort_keys=True)
    optimize(prog)
    assert json.dumps(prog, sort_keys=True) == original


def test_nested_folding():
    """(2 + 3) * (4 + 1) should fold to 25."""
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary(
            "*",
            _binary("+", _lit(2), _lit(3)),
            _binary("+", _lit(4), _lit(1)),
        )},
        {"type": "Print", "args": [_var("x")]},
    ])
    optimized = optimize(prog)
    let_x = optimized["body"][0]
    assert let_x["value"] == {"type": "Literal", "value": 25}
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_dead_code_after_continue():
    """Statements after Continue should be removed."""
    prog = _make_program([
        {"type": "Let", "name": "i", "value": _lit(0)},
        {"type": "While", "test": _binary("<", _var("i"), _lit(5)), "body": [
            {"type": "Assign", "name": "i", "value": _binary("+", _var("i"), _lit(1))},
            {"type": "Continue"},
            {"type": "Print", "args": [_lit("unreachable")]},
        ]},
        {"type": "Print", "args": [_lit("done")]},
    ])
    optimized = optimize(prog)
    while_body = optimized["body"][1]["body"]
    assert len(while_body) == 2  # Only Assign and Continue, Print removed
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_dead_code_after_throw():
    """Statements after Throw should be removed."""
    prog = _make_program([
        {"type": "TryCatch",
         "body": [
             {"type": "Throw", "message": _lit("error")},
             {"type": "Print", "args": [_lit("unreachable")]},
         ],
         "catch_var": "e",
         "catch_body": [
             {"type": "Print", "args": [_var("e")]},
         ]},
    ])
    optimized = optimize(prog)
    try_body = optimized["body"][0]["body"]
    assert len(try_body) == 1  # Only Throw, Print removed
    assert _run_and_capture(prog) == _run_and_capture(optimized)


def test_complex_program_parity():
    """A complex program should produce identical output before and after optimization."""
    prog = _make_program([
        {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
            {"type": "Return", "value": _binary("+", _var("a"), _var("b"))},
        ]},
        {"type": "Let", "name": "base", "value": _binary("+", _lit(10), _lit(0))},
        {"type": "Let", "name": "result", "value": {"type": "Call", "name": "add", "args": [
            _var("base"), _binary("*", _lit(1), _lit(5)),
        ]}},
        {"type": "Print", "args": [_var("result")]},
    ])
    assert _run_and_capture(prog) == _run_and_capture(optimize(prog))


def main() -> None:
    tests = [
        test_constant_folding_arithmetic,
        test_constant_folding_string_concat,
        test_constant_folding_comparison,
        test_no_fold_division_by_zero,
        test_dead_code_after_return,
        test_dead_code_after_break,
        test_dead_code_after_continue,
        test_dead_code_after_throw,
        test_identity_add_zero,
        test_identity_multiply_one,
        test_identity_and_true,
        test_not_folding,
        test_does_not_mutate_input,
        test_nested_folding,
        test_complex_program_parity,
    ]

    print("Running optimizer tests...\n")
    for test in tests:
        test()
        print(f"  {test.__name__}: ✓")

    print(f"\nAll {len(tests)} optimizer tests passed! ✓")


if __name__ == "__main__":
    main()
