"""Tests for Slice operations with negative indexing support.

Run with: python -m tests.test_slice
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil

from tests.test_helpers import verify_backend_parity, TestFailure


def _lit(v):
    return {"type": "Literal", "value": v}


def _var(n):
    return {"type": "Var", "name": n}


def _arr(*values):
    return {"type": "Array", "items": [_lit(v) for v in values]}


def _slice(base, start, end):
    return {"type": "Slice", "base": base, "start": start, "end": end}


def _length(base):
    return {"type": "Length", "base": base}


def _make_doc(body):
    return {"version": "coreil-1.5", "body": body}


def _interp_output(doc):
    buf = io.StringIO()
    with redirect_stdout(buf):
        run_coreil(doc)
    return buf.getvalue()


def _expect_error(doc, test_name):
    """Assert that the interpreter returns a non-zero exit code (runtime error)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        exit_code = run_coreil(doc)
    assert exit_code != 0, (
        f"{test_name}: expected runtime error but got exit code 0, output: {buf.getvalue()!r}"
    )


def test_slice_negative_start():
    """Slice with negative start: arr[-2:5] on [1,2,3,4,5] -> [4, 5]."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(-2), _length(_var("arr")))]},
    ])
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"
    assert _interp_output(doc) == "[4, 5]\n"
    verify_backend_parity(doc, "slice_negative_start")


def test_slice_negative_end():
    """Slice with negative end: arr[0:-1] on [1,2,3,4,5] -> [1, 2, 3, 4]."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(0), _lit(-1))]},
    ])
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"
    assert _interp_output(doc) == "[1, 2, 3, 4]\n"
    verify_backend_parity(doc, "slice_negative_end")


def test_slice_both_negative():
    """Slice with both negative: arr[-4:-1] on [1,2,3,4,5] -> [2, 3, 4]."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(-4), _lit(-1))]},
    ])
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"
    assert _interp_output(doc) == "[2, 3, 4]\n"
    verify_backend_parity(doc, "slice_both_negative")


def test_slice_negative_resolves_to_zero():
    """Slice where negative start resolves to 0: arr[-5:3] on [1,2,3,4,5] -> [1, 2, 3]."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(-5), _lit(3))]},
    ])
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"
    assert _interp_output(doc) == "[1, 2, 3]\n"
    verify_backend_parity(doc, "slice_negative_resolves_to_zero")


def test_slice_negative_empty_result():
    """Slice where resolved start >= resolved end: arr[-1:-3] on [1,2,3,4,5] -> []."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(-1), _lit(-3))]},
    ])
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"
    assert _interp_output(doc) == "[]\n"
    verify_backend_parity(doc, "slice_negative_empty_result")


def test_slice_negative_out_of_bounds():
    """Slice with out-of-bounds negative: arr[-6:3] on [1,2,3,4,5] -> error."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(-6), _lit(3))]},
    ])
    _expect_error(doc, "slice_negative_out_of_bounds")


def test_slice_positive_unchanged():
    """Positive slicing still works: arr[1:4] on [1,2,3,4,5] -> [2, 3, 4]."""
    doc = _make_doc([
        {"type": "Let", "name": "arr", "value": _arr(1, 2, 3, 4, 5)},
        {"type": "Print", "args": [_slice(_var("arr"), _lit(1), _lit(4))]},
    ])
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"
    assert _interp_output(doc) == "[2, 3, 4]\n"
    verify_backend_parity(doc, "slice_positive_unchanged")


def main() -> int:
    print("Running Slice negative indexing tests...\n")

    tests = [
        test_slice_negative_start,
        test_slice_negative_end,
        test_slice_both_negative,
        test_slice_negative_resolves_to_zero,
        test_slice_negative_empty_result,
        test_slice_negative_out_of_bounds,
        test_slice_positive_unchanged,
    ]

    failures = []
    for test in tests:
        try:
            test()
            print(f"  {test.__name__}: passed")
        except (AssertionError, TestFailure) as e:
            failures.append(f"{test.__name__}: {e}")
            print(f"  {test.__name__}: FAILED ({e})")
        except Exception as e:
            failures.append(f"{test.__name__}: {e}")
            print(f"  {test.__name__}: ERROR ({e})")

    print()
    if failures:
        print(f"{len(failures)}/{len(tests)} tests failed:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"All {len(tests)} Slice tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
