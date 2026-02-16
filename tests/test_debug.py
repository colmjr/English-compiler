"""Tests for the Core IL interactive debugger.

Run with:
    python -m tests.test_debug
"""

from __future__ import annotations

import sys
from collections import deque
from typing import Any

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.debug import (
    InteractiveDebugger,
    _format_value,
    _format_stmt,
    debug_coreil,
)


def _make_doc(body: list[dict], version: str = "coreil-1.9") -> dict:
    return {"version": version, "body": body}


# ── step_callback integration tests ──────────────────────────────────────


def test_step_callback_invoked():
    """Counting callback verifies call count matches statement count."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 1}},
        {"type": "Let", "name": "y", "value": {"type": "Literal", "value": 2}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    calls = []

    def counter(stmt, i, local_env, global_env, functions, call_depth):
        calls.append((stmt["type"], i))

    rc = run_coreil(doc, step_callback=counter)
    assert rc == 0, f"expected rc=0, got {rc}"
    assert len(calls) == 3, f"expected 3 calls, got {len(calls)}"
    assert calls[0] == ("Let", 0)
    assert calls[1] == ("Let", 1)
    assert calls[2] == ("Print", 2)


def test_step_callback_receives_correct_data():
    """Verify callback receives correct env contents and types."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 42}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    snapshots = []

    def capture(stmt, i, local_env, global_env, functions, call_depth):
        snapshots.append({
            "type": stmt["type"],
            "index": i,
            "local_env": dict(local_env) if local_env else None,
            "global_env": dict(global_env),
            "call_depth": call_depth,
        })

    rc = run_coreil(doc, step_callback=capture)
    assert rc == 0

    # First statement: Let x = 42 (x not yet in env)
    assert snapshots[0]["type"] == "Let"
    assert snapshots[0]["index"] == 0
    assert snapshots[0]["call_depth"] == 0
    assert snapshots[0]["local_env"] is None
    assert "x" not in snapshots[0]["global_env"]

    # Second statement: Print x (x should now be in env)
    assert snapshots[1]["type"] == "Print"
    assert snapshots[1]["index"] == 1
    assert snapshots[1]["global_env"]["x"] == 42


def test_step_callback_inside_function():
    """Verify call_depth > 0 and local_env populated inside functions."""
    doc = _make_doc([
        {
            "type": "FuncDef",
            "name": "add",
            "params": ["a", "b"],
            "body": [
                {"type": "Return", "value": {
                    "type": "Binary", "op": "+",
                    "left": {"type": "Var", "name": "a"},
                    "right": {"type": "Var", "name": "b"},
                }},
            ],
        },
        {
            "type": "Let", "name": "result",
            "value": {"type": "Call", "name": "add", "args": [
                {"type": "Literal", "value": 3},
                {"type": "Literal", "value": 4},
            ]},
        },
        {"type": "Print", "args": [{"type": "Var", "name": "result"}]},
    ])
    func_calls = []

    def capture(stmt, i, local_env, global_env, functions, call_depth):
        if call_depth > 0:
            func_calls.append({
                "type": stmt["type"],
                "local_env": dict(local_env) if local_env else None,
                "call_depth": call_depth,
            })

    rc = run_coreil(doc, step_callback=capture)
    assert rc == 0
    assert len(func_calls) >= 1, "expected at least one callback inside function"
    assert func_calls[0]["call_depth"] == 1
    assert func_calls[0]["local_env"] is not None
    assert func_calls[0]["local_env"]["a"] == 3
    assert func_calls[0]["local_env"]["b"] == 4


def test_step_callback_none_no_change():
    """Verify None callback has no effect (backward compatibility)."""
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 1}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    rc = run_coreil(doc, step_callback=None)
    assert rc == 0


# ── _format_value tests ──────────────────────────────────────────────────


def test_format_value_primitives():
    assert _format_value(None) == "None"
    assert _format_value(True) == "True"
    assert _format_value(False) == "False"
    assert _format_value(42) == "42"
    assert _format_value(3.14) == "3.14"
    assert _format_value("hello") == "'hello'"


def test_format_value_string_truncation():
    long_str = "x" * 200
    result = _format_value(long_str, max_len=20)
    assert len(result) <= 20
    assert result.endswith("...")


def test_format_value_list():
    result = _format_value([1, 2, 3])
    assert result == "[1, 2, 3]"


def test_format_value_list_truncation():
    big_list = list(range(20))
    result = _format_value(big_list)
    assert "20 items" in result


def test_format_value_tuple():
    result = _format_value((1, 2))
    assert result == "(1, 2)"


def test_format_value_set():
    result = _format_value({1, 2, 3})
    assert "{" in result
    assert "}" in result


def test_format_value_deque():
    result = _format_value(deque([1, 2]))
    assert "deque" in result


def test_format_value_dict():
    result = _format_value({"a": 1})
    assert "'a'" in result
    assert "1" in result


def test_format_value_heap():
    heap = {"_heap_items": [(1, 0, "x")], "_heap_counter": 1}
    result = _format_value(heap)
    assert "heap" in result
    assert "size=1" in result


# ── _format_stmt tests ───────────────────────────────────────────────────


def test_format_stmt():
    assert "Let x" in _format_stmt({"type": "Let", "name": "x"})
    assert "Assign y" in _format_stmt({"type": "Assign", "name": "y"})
    assert "Print" in _format_stmt({"type": "Print", "args": [1, 2]})
    assert "If" in _format_stmt({"type": "If"})
    assert "While" in _format_stmt({"type": "While"})
    assert "For i" in _format_stmt({"type": "For", "var": "i"})
    assert "ForEach x" in _format_stmt({"type": "ForEach", "var": "x"})
    assert "FuncDef add" in _format_stmt({"type": "FuncDef", "name": "add", "params": ["a", "b"]})
    assert "Return" in _format_stmt({"type": "Return"})
    assert "Call foo" in _format_stmt({"type": "Call", "name": "foo"})
    assert "Break" in _format_stmt({"type": "Break"})
    assert "Continue" in _format_stmt({"type": "Continue"})
    assert "Throw" in _format_stmt({"type": "Throw"})
    assert "TryCatch" in _format_stmt({"type": "TryCatch", "catch_var": "e"})


# ── InteractiveDebugger breakpoint management ────────────────────────────


def test_breakpoint_management():
    doc = _make_doc([
        {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 1}},
        {"type": "Let", "name": "y", "value": {"type": "Literal", "value": 2}},
        {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
    ])
    dbg = InteractiveDebugger(doc)

    assert len(dbg.breakpoints) == 0

    dbg.breakpoints.add(0)
    dbg.breakpoints.add(2)
    assert 0 in dbg.breakpoints
    assert 2 in dbg.breakpoints
    assert 1 not in dbg.breakpoints

    dbg.breakpoints.discard(0)
    assert 0 not in dbg.breakpoints
    assert len(dbg.breakpoints) == 1


# ── Run all tests ────────────────────────────────────────────────────────


def _run_tests():
    tests = [
        test_step_callback_invoked,
        test_step_callback_receives_correct_data,
        test_step_callback_inside_function,
        test_step_callback_none_no_change,
        test_format_value_primitives,
        test_format_value_string_truncation,
        test_format_value_list,
        test_format_value_list_truncation,
        test_format_value_tuple,
        test_format_value_set,
        test_format_value_deque,
        test_format_value_dict,
        test_format_value_heap,
        test_format_stmt,
        test_breakpoint_management,
    ]

    passed = 0
    failed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {name}: {exc}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_tests())
