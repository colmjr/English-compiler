"""Tests for Break and Continue statements (Core IL v1.7).

Tests cover:
- Basic break in while loop
- Basic continue in while loop
- Break/continue in for loop (after lowering)
- Nested loops (only innermost affected)
- Validation errors when outside loop
- Break inside function inside loop (should error)
- Backend parity (interpreter == Python backend)
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from typing import Any

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.validate import validate_coreil


def _run_interp(doc: dict) -> str:
    """Run interpreter and capture output."""
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = run_coreil(doc)
    assert exit_code == 0, f"Interpreter failed with exit code {exit_code}"
    return stdout.getvalue()


def _run_python(doc: dict) -> str:
    """Generate Python code and execute it."""
    code = emit_python(doc)
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exec(code, {})
    return stdout.getvalue()


def _make_doc(body: list[dict]) -> dict:
    """Create a v1.7 Core IL document with the given body."""
    return {"version": "coreil-1.7", "body": body}


class TestBreakBasic:
    """Test basic Break functionality."""

    def test_break_in_while(self):
        """Break exits the while loop."""
        doc = _make_doc([
            {"type": "Let", "name": "i", "value": {"type": "Literal", "value": 0}},
            {
                "type": "While",
                "test": {"type": "Binary", "op": "<", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 10}},
                "body": [
                    {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 3}},
                        "then": [{"type": "Break"}],
                    },
                    {"type": "Assign", "name": "i", "value": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}}},
                ],
            },
            {"type": "Print", "args": [{"type": "Literal", "value": "done"}]},
        ])

        output = _run_interp(doc)
        assert output == "0\n1\n2\n3\ndone\n"

    def test_break_in_for(self):
        """Break works in for loop (after lowering)."""
        doc = _make_doc([
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 10}},
                "body": [
                    {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 2}},
                        "then": [{"type": "Break"}],
                    },
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "0\n1\n2\n"

    def test_break_in_foreach(self):
        """Break works in foreach loop."""
        doc = _make_doc([
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [
                {"type": "Literal", "value": "a"},
                {"type": "Literal", "value": "b"},
                {"type": "Literal", "value": "c"},
                {"type": "Literal", "value": "d"},
            ]}},
            {
                "type": "ForEach",
                "var": "x",
                "iter": {"type": "Var", "name": "arr"},
                "body": [
                    {"type": "Print", "args": [{"type": "Var", "name": "x"}]},
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "x"}, "right": {"type": "Literal", "value": "b"}},
                        "then": [{"type": "Break"}],
                    },
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "a\nb\n"


class TestContinueBasic:
    """Test basic Continue functionality."""

    def test_continue_in_while(self):
        """Continue skips to next iteration."""
        doc = _make_doc([
            {"type": "Let", "name": "i", "value": {"type": "Literal", "value": 0}},
            {
                "type": "While",
                "test": {"type": "Binary", "op": "<", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 5}},
                "body": [
                    {"type": "Assign", "name": "i", "value": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}}},
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 3}},
                        "then": [{"type": "Continue"}],
                    },
                    {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
                ],
            },
        ])

        output = _run_interp(doc)
        # Prints 1, 2, 4, 5 (skips 3)
        assert output == "1\n2\n4\n5\n"

    def test_continue_in_for(self):
        """Continue works in for loop (after lowering)."""
        doc = _make_doc([
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 5}},
                "body": [
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 2}},
                        "then": [{"type": "Continue"}],
                    },
                    {"type": "Print", "args": [{"type": "Var", "name": "i"}]},
                ],
            },
        ])

        output = _run_interp(doc)
        # Prints 0, 1, 3, 4 (skips 2)
        assert output == "0\n1\n3\n4\n"


class TestNestedLoops:
    """Test Break/Continue with nested loops."""

    def test_nested_loop_break(self):
        """Break only exits innermost loop."""
        doc = _make_doc([
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 3}},
                "body": [
                    {"type": "Print", "args": [{"type": "Literal", "value": "outer"}, {"type": "Var", "name": "i"}]},
                    {
                        "type": "For",
                        "var": "j",
                        "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 3}},
                        "body": [
                            {
                                "type": "If",
                                "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "j"}, "right": {"type": "Literal", "value": 1}},
                                "then": [{"type": "Break"}],
                            },
                            {"type": "Print", "args": [{"type": "Literal", "value": "inner"}, {"type": "Var", "name": "j"}]},
                        ],
                    },
                ],
            },
        ])

        output = _run_interp(doc)
        # Outer loop runs 3 times, inner loop breaks after printing j=0 each time
        expected = "outer 0\ninner 0\nouter 1\ninner 0\nouter 2\ninner 0\n"
        assert output == expected

    def test_nested_loop_continue(self):
        """Continue only affects innermost loop."""
        doc = _make_doc([
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 2}},
                "body": [
                    {
                        "type": "For",
                        "var": "j",
                        "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 3}},
                        "body": [
                            {
                                "type": "If",
                                "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "j"}, "right": {"type": "Literal", "value": 1}},
                                "then": [{"type": "Continue"}],
                            },
                            {"type": "Print", "args": [{"type": "Var", "name": "i"}, {"type": "Var", "name": "j"}]},
                        ],
                    },
                ],
            },
        ])

        output = _run_interp(doc)
        # Prints (0,0), (0,2), (1,0), (1,2) - skips j=1
        expected = "0 0\n0 2\n1 0\n1 2\n"
        assert output == expected


class TestValidation:
    """Test validation errors for Break/Continue."""

    def test_break_outside_loop_error(self):
        """Break outside a loop is a validation error."""
        doc = _make_doc([
            {"type": "Break"},
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 1
        assert "Break is only allowed inside a loop" in errors[0]["message"]

    def test_continue_outside_loop_error(self):
        """Continue outside a loop is a validation error."""
        doc = _make_doc([
            {"type": "Continue"},
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 1
        assert "Continue is only allowed inside a loop" in errors[0]["message"]

    def test_break_in_if_outside_loop_error(self):
        """Break inside if but outside loop is an error."""
        doc = _make_doc([
            {
                "type": "If",
                "test": {"type": "Literal", "value": True},
                "then": [{"type": "Break"}],
            },
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 1
        assert "Break is only allowed inside a loop" in errors[0]["message"]

    def test_break_in_function_in_loop_error(self):
        """Break inside a function defined inside a loop is an error."""
        doc = _make_doc([
            {
                "type": "While",
                "test": {"type": "Literal", "value": True},
                "body": [
                    {
                        "type": "FuncDef",
                        "name": "inner",
                        "params": [],
                        "body": [{"type": "Break"}],
                    },
                ],
            },
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 1
        assert "Break is only allowed inside a loop" in errors[0]["message"]

    def test_continue_in_function_in_loop_error(self):
        """Continue inside a function defined inside a loop is an error."""
        doc = _make_doc([
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 5}},
                "body": [
                    {
                        "type": "FuncDef",
                        "name": "inner",
                        "params": [],
                        "body": [{"type": "Continue"}],
                    },
                ],
            },
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 1
        assert "Continue is only allowed inside a loop" in errors[0]["message"]

    def test_break_in_loop_valid(self):
        """Break inside a loop is valid."""
        doc = _make_doc([
            {
                "type": "While",
                "test": {"type": "Literal", "value": True},
                "body": [{"type": "Break"}],
            },
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 0


class TestBackendParity:
    """Test that interpreter and Python backend produce identical output."""

    def test_break_parity(self):
        """Break produces same output in interpreter and Python."""
        doc = _make_doc([
            {"type": "Let", "name": "result", "value": {"type": "Array", "items": []}},
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 10}},
                "body": [
                    {"type": "Push", "base": {"type": "Var", "name": "result"}, "value": {"type": "Var", "name": "i"}},
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 4}},
                        "then": [{"type": "Break"}],
                    },
                ],
            },
            {"type": "Print", "args": [{"type": "Var", "name": "result"}]},
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output

    def test_continue_parity(self):
        """Continue produces same output in interpreter and Python."""
        doc = _make_doc([
            {"type": "Let", "name": "result", "value": {"type": "Array", "items": []}},
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 6}},
                "body": [
                    {
                        "type": "If",
                        "test": {"type": "Binary", "op": "==", "left": {"type": "Binary", "op": "%", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 2}}, "right": {"type": "Literal", "value": 0}},
                        "then": [{"type": "Continue"}],
                    },
                    {"type": "Push", "base": {"type": "Var", "name": "result"}, "value": {"type": "Var", "name": "i"}},
                ],
            },
            {"type": "Print", "args": [{"type": "Var", "name": "result"}]},
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output

    def test_nested_break_continue_parity(self):
        """Nested break/continue produces same output in both backends."""
        doc = _make_doc([
            {"type": "Let", "name": "output", "value": {"type": "Array", "items": []}},
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 3}},
                "body": [
                    {
                        "type": "For",
                        "var": "j",
                        "iter": {"type": "Range", "from": {"type": "Literal", "value": 0}, "to": {"type": "Literal", "value": 5}},
                        "body": [
                            {
                                "type": "If",
                                "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "j"}, "right": {"type": "Literal", "value": 1}},
                                "then": [{"type": "Continue"}],
                            },
                            {
                                "type": "If",
                                "test": {"type": "Binary", "op": "==", "left": {"type": "Var", "name": "j"}, "right": {"type": "Literal", "value": 3}},
                                "then": [{"type": "Break"}],
                            },
                            {"type": "Push", "base": {"type": "Var", "name": "output"}, "value": {"type": "Tuple", "items": [{"type": "Var", "name": "i"}, {"type": "Var", "name": "j"}]}},
                        ],
                    },
                ],
            },
            {"type": "Print", "args": [{"type": "Var", "name": "output"}]},
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output
