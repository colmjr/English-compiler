"""Tests for TryCatch and Throw statements (Core IL v1.8).

Tests cover:
- Basic Throw inside TryCatch
- Runtime error catch (division by zero)
- Index out of bounds catch
- Finally always runs (success and error paths)
- Nested TryCatch
- Throw in catch (re-throwing)
- Control flow in try (Return/Break/Continue propagate, finally still runs)
- Throw outside TryCatch (crashes the program)
- Validation errors (missing required fields)
- Backend parity (interpreter == Python backend)
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

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


def _run_interp_error(doc: dict) -> str:
    """Run interpreter expecting an error, capture output."""
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = run_coreil(doc)
    assert exit_code == 1, f"Expected error (exit code 1) but got {exit_code}"
    return stdout.getvalue()


def _run_python(doc: dict) -> str:
    """Generate Python code and execute it."""
    code = emit_python(doc)
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exec(code, {})
    return stdout.getvalue()


def _make_doc(body: list[dict]) -> dict:
    """Create a v1.8 Core IL document with the given body."""
    return {"version": "coreil-1.8", "body": body}


def _lit(value) -> dict:
    return {"type": "Literal", "value": value}


def _var(name: str) -> dict:
    return {"type": "Var", "name": name}


def _bin(op: str, left: dict, right: dict) -> dict:
    return {"type": "Binary", "op": op, "left": left, "right": right}


class TestThrowBasic:
    """Test basic Throw functionality."""

    def test_throw_caught_by_try_catch(self):
        """Throw inside TryCatch, verify catch_var gets the message."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Throw", "message": _lit("something went wrong")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("caught:"), _var("e")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "caught: something went wrong\n"

    def test_throw_with_expression_message(self):
        """Throw with a computed message expression."""
        doc = _make_doc([
            {"type": "Let", "name": "code", "value": _lit("404")},
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Throw", "message": _bin("+", _lit("error code: "), _var("code"))},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_var("e")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "error code: 404\n"

    def test_throw_outside_try_catch_crashes(self):
        """Throw outside TryCatch is a runtime error."""
        doc = _make_doc([
            {"type": "Throw", "message": _lit("uncaught error")},
        ])

        output = _run_interp_error(doc)
        assert "uncaught error" in output


class TestRuntimeErrorCatch:
    """Test catching runtime errors."""

    def test_division_by_zero(self):
        """Division by zero inside TryCatch is caught."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Let", "name": "x", "value": _bin("/", _lit(1), _lit(0))},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("caught division error")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "caught division error\n"

    def test_index_out_of_bounds(self):
        """Index out of bounds inside TryCatch is caught."""
        doc = _make_doc([
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [_lit(1), _lit(2)]}},
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Let", "name": "x", "value": {"type": "Index", "base": _var("arr"), "index": _lit(10)}},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("caught index error")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "caught index error\n"


class TestFinally:
    """Test finally_body behavior."""

    def test_finally_runs_on_success(self):
        """finally_body runs even when no error occurs."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Print", "args": [_lit("try")]},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("catch")]},
                ],
                "finally_body": [
                    {"type": "Print", "args": [_lit("finally")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "try\nfinally\n"

    def test_finally_runs_on_error(self):
        """finally_body runs when an error is caught."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Print", "args": [_lit("try")]},
                    {"type": "Throw", "message": _lit("oops")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("catch")]},
                ],
                "finally_body": [
                    {"type": "Print", "args": [_lit("finally")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "try\ncatch\nfinally\n"

    def test_no_finally(self):
        """TryCatch without finally_body works fine."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Throw", "message": _lit("err")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_var("e")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "err\n"


class TestNestedTryCatch:
    """Test nested TryCatch behavior."""

    def test_inner_catch_doesnt_affect_outer(self):
        """Inner TryCatch catches its own error, outer doesn't trigger."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Print", "args": [_lit("outer try")]},
                    {
                        "type": "TryCatch",
                        "body": [
                            {"type": "Throw", "message": _lit("inner error")},
                        ],
                        "catch_var": "e",
                        "catch_body": [
                            {"type": "Print", "args": [_lit("inner catch:"), _var("e")]},
                        ],
                    },
                    {"type": "Print", "args": [_lit("after inner")]},
                ],
                "catch_var": "e2",
                "catch_body": [
                    {"type": "Print", "args": [_lit("outer catch")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "outer try\ninner catch: inner error\nafter inner\n"

    def test_rethrow_from_catch(self):
        """Throwing from catch block propagates to outer TryCatch."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {
                        "type": "TryCatch",
                        "body": [
                            {"type": "Throw", "message": _lit("original")},
                        ],
                        "catch_var": "e",
                        "catch_body": [
                            {"type": "Throw", "message": _bin("+", _lit("rethrown: "), _var("e"))},
                        ],
                    },
                ],
                "catch_var": "e2",
                "catch_body": [
                    {"type": "Print", "args": [_var("e2")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "rethrown: original\n"


class TestControlFlowInTry:
    """Test that control flow signals propagate through TryCatch."""

    def test_return_propagates_through_try(self):
        """Return inside try body propagates out of function, finally still runs."""
        doc = _make_doc([
            {
                "type": "FuncDef",
                "name": "f",
                "params": [],
                "body": [
                    {
                        "type": "TryCatch",
                        "body": [
                            {"type": "Print", "args": [_lit("before return")]},
                            {"type": "Return", "value": _lit(42)},
                        ],
                        "catch_var": "e",
                        "catch_body": [
                            {"type": "Print", "args": [_lit("catch")]},
                        ],
                        "finally_body": [
                            {"type": "Print", "args": [_lit("finally")]},
                        ],
                    },
                    {"type": "Print", "args": [_lit("after try")]},
                    {"type": "Return", "value": _lit(0)},
                ],
            },
            {"type": "Let", "name": "result", "value": {"type": "Call", "name": "f", "args": []}},
            {"type": "Print", "args": [_var("result")]},
        ])

        output = _run_interp(doc)
        assert output == "before return\nfinally\n42\n"

    def test_break_propagates_through_try(self):
        """Break inside try body propagates out of loop, finally still runs."""
        doc = _make_doc([
            {
                "type": "For",
                "var": "i",
                "iter": {"type": "Range", "from": _lit(0), "to": _lit(5)},
                "body": [
                    {
                        "type": "TryCatch",
                        "body": [
                            {"type": "Print", "args": [_var("i")]},
                            {
                                "type": "If",
                                "test": _bin("==", _var("i"), _lit(2)),
                                "then": [{"type": "Break"}],
                            },
                        ],
                        "catch_var": "e",
                        "catch_body": [],
                        "finally_body": [
                            {"type": "Print", "args": [_lit("f")]},
                        ],
                    },
                ],
            },
            {"type": "Print", "args": [_lit("done")]},
        ])

        output = _run_interp(doc)
        assert output == "0\nf\n1\nf\n2\nf\ndone\n"


class TestNoErrorPath:
    """Test TryCatch when no error occurs."""

    def test_no_error_skips_catch(self):
        """When body succeeds, catch_body is skipped."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Print", "args": [_lit("ok")]},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("error")]},
                ],
            },
        ])

        output = _run_interp(doc)
        assert output == "ok\n"


class TestValidation:
    """Test validation errors for Throw and TryCatch."""

    def test_throw_missing_message(self):
        """Throw without message is a validation error."""
        doc = _make_doc([
            {"type": "Throw"},
        ])

        errors = validate_coreil(doc)
        assert len(errors) >= 1
        assert any("message" in e["message"] for e in errors)

    def test_try_catch_missing_body(self):
        """TryCatch missing body is a validation error."""
        doc = _make_doc([
            {"type": "TryCatch", "catch_var": "e", "catch_body": []},
        ])

        errors = validate_coreil(doc)
        assert len(errors) >= 1
        assert any("body" in e["message"] for e in errors)

    def test_try_catch_missing_catch_var(self):
        """TryCatch missing catch_var is a validation error."""
        doc = _make_doc([
            {"type": "TryCatch", "body": [], "catch_body": []},
        ])

        errors = validate_coreil(doc)
        assert len(errors) >= 1
        assert any("catch_var" in e["message"] for e in errors)

    def test_try_catch_missing_catch_body(self):
        """TryCatch missing catch_body is a validation error."""
        doc = _make_doc([
            {"type": "TryCatch", "body": [], "catch_var": "e"},
        ])

        errors = validate_coreil(doc)
        assert len(errors) >= 1
        assert any("catch_body" in e["message"] for e in errors)

    def test_valid_try_catch(self):
        """Valid TryCatch passes validation."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Throw", "message": _lit("test")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_var("e")]},
                ],
            },
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 0

    def test_catch_var_defined_in_catch_body(self):
        """catch_var is available in catch_body."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Throw", "message": _lit("test")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_var("e")]},
                ],
            },
        ])

        errors = validate_coreil(doc)
        assert len(errors) == 0


class TestBackendParity:
    """Test that interpreter and Python backend produce identical output."""

    def test_basic_throw_catch_parity(self):
        """Basic throw/catch produces same output in both backends."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Throw", "message": _lit("test error")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("caught:"), _var("e")]},
                ],
            },
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output

    def test_runtime_error_parity(self):
        """Runtime error catch produces same output in both backends."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Let", "name": "arr", "value": {"type": "Array", "items": [_lit(1)]}},
                    {"type": "Let", "name": "x", "value": {"type": "Index", "base": _var("arr"), "index": _lit(99)}},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("caught error")]},
                ],
            },
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output

    def test_finally_parity(self):
        """Finally block produces same output in both backends."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Print", "args": [_lit("try")]},
                    {"type": "Throw", "message": _lit("oops")},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("catch")]},
                ],
                "finally_body": [
                    {"type": "Print", "args": [_lit("finally")]},
                ],
            },
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output

    def test_no_error_parity(self):
        """No-error path produces same output in both backends."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {"type": "Print", "args": [_lit("ok")]},
                ],
                "catch_var": "e",
                "catch_body": [
                    {"type": "Print", "args": [_lit("error")]},
                ],
                "finally_body": [
                    {"type": "Print", "args": [_lit("done")]},
                ],
            },
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output

    def test_nested_try_catch_parity(self):
        """Nested try/catch produces same output in both backends."""
        doc = _make_doc([
            {
                "type": "TryCatch",
                "body": [
                    {
                        "type": "TryCatch",
                        "body": [
                            {"type": "Throw", "message": _lit("inner")},
                        ],
                        "catch_var": "e1",
                        "catch_body": [
                            {"type": "Print", "args": [_lit("inner catch:"), _var("e1")]},
                            {"type": "Throw", "message": _lit("rethrown")},
                        ],
                    },
                ],
                "catch_var": "e2",
                "catch_body": [
                    {"type": "Print", "args": [_lit("outer catch:"), _var("e2")]},
                ],
            },
        ])

        interp_output = _run_interp(doc)
        python_output = _run_python(doc)
        assert interp_output == python_output
