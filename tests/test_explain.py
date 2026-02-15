"""Tests for the reverse compiler (Core IL → English explanation)."""

from __future__ import annotations

from english_compiler.explain import explain


def _make_program(body: list[dict], version: str = "coreil-1.9") -> dict:
    return {"version": version, "body": body}


def _lit(value) -> dict:
    return {"type": "Literal", "value": value}


def _var(name: str) -> dict:
    return {"type": "Var", "name": name}


def _binary(op: str, left: dict, right: dict) -> dict:
    return {"type": "Binary", "op": op, "left": left, "right": right}


def test_empty_program():
    result = explain({"version": "coreil-1.9", "body": []})
    assert "empty body" in result.lower()


def test_invalid_input():
    assert "Error" in explain("not a dict")
    assert "Error" in explain({"version": "coreil-1.9"})


def test_let_statement():
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _lit(42)},
    ])
    result = explain(prog)
    assert "x" in result
    assert "42" in result


def test_assign_statement():
    prog = _make_program([
        {"type": "Assign", "name": "x", "value": _lit(10)},
    ])
    result = explain(prog)
    assert "Update" in result
    assert "x" in result


def test_print_statement():
    prog = _make_program([
        {"type": "Print", "args": [_lit("hello")]},
    ])
    result = explain(prog)
    assert "Print" in result
    assert "hello" in result


def test_if_else():
    prog = _make_program([
        {"type": "If", "test": _binary(">", _var("x"), _lit(0)),
         "then": [{"type": "Print", "args": [_lit("positive")]}],
         "else": [{"type": "Print", "args": [_lit("non-positive")]}]},
    ])
    result = explain(prog)
    assert "If" in result
    assert "Otherwise" in result


def test_while_loop():
    prog = _make_program([
        {"type": "While", "test": _binary("<", _var("i"), _lit(10)),
         "body": [{"type": "Assign", "name": "i", "value": _binary("+", _var("i"), _lit(1))}]},
    ])
    result = explain(prog)
    assert "While" in result


def test_for_loop_range():
    prog = _make_program([
        {"type": "For", "var": "i",
         "iter": {"type": "Range", "from": _lit(0), "to": _lit(10), "inclusive": False},
         "body": [{"type": "Print", "args": [_var("i")]}]},
    ])
    result = explain(prog)
    assert "For" in result
    assert "i" in result


def test_funcdef():
    prog = _make_program([
        {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
            {"type": "Return", "value": _binary("+", _var("a"), _var("b"))},
        ]},
    ])
    result = explain(prog)
    assert "add" in result
    assert "Return" in result


def test_try_catch_finally():
    prog = _make_program([
        {"type": "TryCatch", "body": [
            {"type": "Throw", "message": _lit("oops")},
        ], "catch_var": "err", "catch_body": [
            {"type": "Print", "args": [_var("err")]},
        ], "finally_body": [
            {"type": "Print", "args": [_lit("cleanup")]},
        ]},
    ])
    result = explain(prog)
    assert "Try" in result
    assert "err" in result
    assert "Finally" in result


def test_summary_with_functions():
    prog = _make_program([
        {"type": "FuncDef", "name": "foo", "params": [], "body": [
            {"type": "Return", "value": _lit(1)},
        ]},
        {"type": "Print", "args": [_lit("hi")]},
    ])
    result = explain(prog)
    assert "foo" in result
    assert "prints output" in result.lower()


def test_verbose_mode():
    prog = _make_program([
        {"type": "Let", "name": "x", "value": _binary("+", _lit(1), _lit(2))},
    ])
    normal = explain(prog)
    verbose = explain(prog, verbose=True)
    # Verbose should use words like "plus" instead of "+"
    assert "plus" in verbose
    assert "plus" not in normal


def test_break_continue():
    prog = _make_program([
        {"type": "While", "test": _lit(True), "body": [
            {"type": "Break"},
        ]},
        {"type": "While", "test": _lit(True), "body": [
            {"type": "Continue"},
        ]},
    ])
    result = explain(prog)
    assert "Break" in result
    assert "Continue" in result


def test_array_map_expressions():
    prog = _make_program([
        {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [_lit(1), _lit(2)]}},
        {"type": "Let", "name": "m", "value": {"type": "Map", "items": [
            {"key": _lit("a"), "value": _lit(1)},
        ]}},
    ])
    result = explain(prog)
    assert "[1, 2]" in result
    assert '"a"' in result


def main() -> None:
    tests = [
        test_empty_program,
        test_invalid_input,
        test_let_statement,
        test_assign_statement,
        test_print_statement,
        test_if_else,
        test_while_loop,
        test_for_loop_range,
        test_funcdef,
        test_try_catch_finally,
        test_summary_with_functions,
        test_verbose_mode,
        test_break_continue,
        test_array_map_expressions,
    ]

    print("Running explain tests...\n")
    for test in tests:
        test()
        print(f"  {test.__name__}: pass")

    print(f"\nAll {len(tests)} explain tests passed!")


if __name__ == "__main__":
    main()
