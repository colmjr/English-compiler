"""Tests for type conversion expressions (Core IL v1.9).

Tests cover:
- ToInt: float→int, string→int, int→int passthrough
- ToFloat: int→float, string→float, float→float passthrough
- ToString: int→string, float→string, bool→string, None→string
- Error cases: invalid conversions (bool→int, bool→float, non-numeric strings, list)
- Validation: missing required fields
- Backend parity: interpreter == Python backend
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
    code, _ = emit_python(doc)
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exec(code, {})
    return stdout.getvalue()


def _make_doc(body: list[dict]) -> dict:
    """Create a v1.9 Core IL document with the given body."""
    return {"version": "coreil-1.9", "body": body}


def _lit(value) -> dict:
    return {"type": "Literal", "value": value}


def _var(name: str) -> dict:
    return {"type": "Var", "name": name}


# ============================================================
# ToInt tests
# ============================================================

class TestToInt:
    """Test ToInt type conversion."""

    def test_float_to_int(self):
        """ToInt truncates floats toward zero."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(3.7)}]},
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(-2.9)}]},
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(0.0)}]},
        ])
        output = _run_interp(doc)
        assert output == "3\n-2\n0\n", f"Got: {output!r}"

    def test_string_to_int(self):
        """ToInt parses numeric strings."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit("42")}]},
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit("-7")}]},
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit("0")}]},
        ])
        output = _run_interp(doc)
        assert output == "42\n-7\n0\n", f"Got: {output!r}"

    def test_int_passthrough(self):
        """ToInt on an int returns the same value."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(99)}]},
        ])
        output = _run_interp(doc)
        assert output == "99\n", f"Got: {output!r}"

    def test_error_non_numeric_string(self):
        """ToInt on a non-numeric string raises an error."""
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "ToInt", "value": _lit("abc")}},
        ])
        output = _run_interp_error(doc)
        assert "cannot convert" in output.lower() or "error" in output.lower()

    def test_error_bool(self):
        """ToInt rejects booleans (booleans are not integers in Core IL)."""
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "ToInt", "value": _lit(True)}},
        ])
        output = _run_interp_error(doc)
        assert "cannot convert" in output.lower() or "error" in output.lower()

    def test_error_list(self):
        """ToInt rejects lists."""
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "ToInt", "value": {"type": "Array", "items": [_lit(1)]}}},
        ])
        output = _run_interp_error(doc)
        assert "cannot convert" in output.lower() or "error" in output.lower()


# ============================================================
# ToFloat tests
# ============================================================

class TestToFloat:
    """Test ToFloat type conversion."""

    def test_int_to_float(self):
        """ToFloat converts ints to floats."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(5)}]},
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(-3)}]},
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(0)}]},
        ])
        output = _run_interp(doc)
        assert output == "5.0\n-3.0\n0.0\n", f"Got: {output!r}"

    def test_string_to_float(self):
        """ToFloat parses numeric strings."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit("3.14")}]},
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit("-2.5")}]},
        ])
        output = _run_interp(doc)
        assert output == "3.14\n-2.5\n", f"Got: {output!r}"

    def test_float_passthrough(self):
        """ToFloat on a float returns the same value."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(1.5)}]},
        ])
        output = _run_interp(doc)
        assert output == "1.5\n", f"Got: {output!r}"

    def test_error_non_numeric_string(self):
        """ToFloat on a non-numeric string raises an error."""
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "ToFloat", "value": _lit("xyz")}},
        ])
        output = _run_interp_error(doc)
        assert "cannot convert" in output.lower() or "error" in output.lower()

    def test_error_bool(self):
        """ToFloat rejects booleans."""
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "ToFloat", "value": _lit(False)}},
        ])
        output = _run_interp_error(doc)
        assert "cannot convert" in output.lower() or "error" in output.lower()


# ============================================================
# ToString tests
# ============================================================

class TestToString:
    """Test ToString type conversion."""

    def test_int_to_string(self):
        """ToString converts ints to their string representation."""
        doc = _make_doc([
            {"type": "Let", "name": "s", "value": {"type": "ToString", "value": _lit(123)}},
            {"type": "Print", "args": [_var("s")]},
            {"type": "Print", "args": [
                {"type": "Binary", "op": "+", "left": _lit("num="), "right": _var("s")},
            ]},
        ])
        output = _run_interp(doc)
        assert output == "123\nnum=123\n", f"Got: {output!r}"

    def test_float_to_string(self):
        """ToString converts floats to their string representation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(3.14)}]},
        ])
        output = _run_interp(doc)
        assert output == "3.14\n", f"Got: {output!r}"

    def test_bool_to_string(self):
        """ToString converts booleans to 'True'/'False'."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(True)}]},
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(False)}]},
        ])
        output = _run_interp(doc)
        assert output == "True\nFalse\n", f"Got: {output!r}"

    def test_none_to_string(self):
        """ToString converts None to 'None'."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(None)}]},
        ])
        output = _run_interp(doc)
        assert output == "None\n", f"Got: {output!r}"


# ============================================================
# Validation tests
# ============================================================

class TestValidation:
    """Test validation of type conversion nodes."""

    def test_valid_to_int(self):
        """Valid ToInt passes validation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(3.5)}]},
        ])
        errors = validate_coreil(doc)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_valid_to_float(self):
        """Valid ToFloat passes validation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(5)}]},
        ])
        errors = validate_coreil(doc)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_valid_to_string(self):
        """Valid ToString passes validation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(42)}]},
        ])
        errors = validate_coreil(doc)
        assert errors == [], f"Unexpected errors: {errors}"

    def test_missing_value_to_int(self):
        """ToInt without 'value' field should fail validation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToInt"}]},
        ])
        errors = validate_coreil(doc)
        assert len(errors) > 0, "Expected validation error for missing 'value'"

    def test_missing_value_to_float(self):
        """ToFloat without 'value' field should fail validation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToFloat"}]},
        ])
        errors = validate_coreil(doc)
        assert len(errors) > 0, "Expected validation error for missing 'value'"

    def test_missing_value_to_string(self):
        """ToString without 'value' field should fail validation."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToString"}]},
        ])
        errors = validate_coreil(doc)
        assert len(errors) > 0, "Expected validation error for missing 'value'"


# ============================================================
# Backend parity tests (interpreter == Python backend)
# ============================================================

class TestParity:
    """Test that interpreter and Python backend produce identical output."""

    def test_parity_to_int(self):
        """ToInt produces same output in interpreter and Python."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(3.7)}]},
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit("42")}]},
            {"type": "Print", "args": [{"type": "ToInt", "value": _lit(99)}]},
        ])
        assert _run_interp(doc) == _run_python(doc)

    def test_parity_to_float(self):
        """ToFloat produces same output in interpreter and Python."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(5)}]},
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit("3.14")}]},
            {"type": "Print", "args": [{"type": "ToFloat", "value": _lit(1.5)}]},
        ])
        assert _run_interp(doc) == _run_python(doc)

    def test_parity_to_string(self):
        """ToString produces same output in interpreter and Python."""
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(123)}]},
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(3.14)}]},
            {"type": "Print", "args": [{"type": "ToString", "value": _lit(None)}]},
        ])
        assert _run_interp(doc) == _run_python(doc)

    def test_parity_chained_conversions(self):
        """Chained conversions: int→string→int round-trip."""
        doc = _make_doc([
            {"type": "Let", "name": "n", "value": _lit(42)},
            {"type": "Let", "name": "s", "value": {"type": "ToString", "value": _var("n")}},
            {"type": "Let", "name": "back", "value": {"type": "ToInt", "value": _var("s")}},
            {"type": "Print", "args": [_var("back")]},
        ])
        assert _run_interp(doc) == _run_python(doc)

    def test_parity_conversion_in_expression(self):
        """Type conversion used inside arithmetic expression."""
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "ToInt", "value": _lit(3.9)}},
            {"type": "Print", "args": [
                {"type": "Binary", "op": "+", "left": _var("x"), "right": _lit(10)},
            ]},
        ])
        assert _run_interp(doc) == _run_python(doc)


# ============================================================
# Runner
# ============================================================

def main() -> int:
    tests = [
        # ToInt
        ("ToInt: float→int", TestToInt().test_float_to_int),
        ("ToInt: string→int", TestToInt().test_string_to_int),
        ("ToInt: int passthrough", TestToInt().test_int_passthrough),
        ("ToInt: error non-numeric string", TestToInt().test_error_non_numeric_string),
        ("ToInt: error bool", TestToInt().test_error_bool),
        ("ToInt: error list", TestToInt().test_error_list),
        # ToFloat
        ("ToFloat: int→float", TestToFloat().test_int_to_float),
        ("ToFloat: string→float", TestToFloat().test_string_to_float),
        ("ToFloat: float passthrough", TestToFloat().test_float_passthrough),
        ("ToFloat: error non-numeric string", TestToFloat().test_error_non_numeric_string),
        ("ToFloat: error bool", TestToFloat().test_error_bool),
        # ToString
        ("ToString: int→string", TestToString().test_int_to_string),
        ("ToString: float→string", TestToString().test_float_to_string),
        ("ToString: bool→string", TestToString().test_bool_to_string),
        ("ToString: None→string", TestToString().test_none_to_string),
        # Validation
        ("Validation: valid ToInt", TestValidation().test_valid_to_int),
        ("Validation: valid ToFloat", TestValidation().test_valid_to_float),
        ("Validation: valid ToString", TestValidation().test_valid_to_string),
        ("Validation: missing value ToInt", TestValidation().test_missing_value_to_int),
        ("Validation: missing value ToFloat", TestValidation().test_missing_value_to_float),
        ("Validation: missing value ToString", TestValidation().test_missing_value_to_string),
        # Parity
        ("Parity: ToInt", TestParity().test_parity_to_int),
        ("Parity: ToFloat", TestParity().test_parity_to_float),
        ("Parity: ToString", TestParity().test_parity_to_string),
        ("Parity: chained conversions", TestParity().test_parity_chained_conversions),
        ("Parity: conversion in expression", TestParity().test_parity_conversion_in_expression),
    ]

    print("Running type conversion tests (Core IL v1.9)...\n")
    failures = []
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  {name}: ✓")
        except (AssertionError, Exception) as e:
            failures.append(f"{name}: {e}")
            print(f"  {name}: ✗ ({e})")

    print()
    if failures:
        print(f"{len(failures)}/{len(tests)} tests FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(tests)} type conversion tests passed! ✓")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
