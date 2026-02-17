"""Tests for Switch-Case statement (Core IL v1.10)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from english_compiler.coreil.validate import validate_coreil
from tests.test_helpers import TestFailure, verify_backend_parity


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _switch_basic() -> dict:
    """Switch with 3 cases, matching case 2."""
    return {
        "version": "coreil-1.10",
        "body": [
            {
                "type": "Let",
                "name": "x",
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "Switch",
                "test": {"type": "Var", "name": "x"},
                "cases": [
                    {
                        "value": {"type": "Literal", "value": 1},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "one"}]}],
                    },
                    {
                        "value": {"type": "Literal", "value": 2},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "two"}]}],
                    },
                    {
                        "value": {"type": "Literal", "value": 3},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "three"}]}],
                    },
                ],
            },
        ],
    }


def _switch_with_default() -> dict:
    """Switch that falls to default."""
    return {
        "version": "coreil-1.10",
        "body": [
            {
                "type": "Let",
                "name": "x",
                "value": {"type": "Literal", "value": 99},
            },
            {
                "type": "Switch",
                "test": {"type": "Var", "name": "x"},
                "cases": [
                    {
                        "value": {"type": "Literal", "value": 1},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "one"}]}],
                    },
                ],
                "default": [
                    {"type": "Print", "args": [{"type": "Literal", "value": "default"}]},
                ],
            },
        ],
    }


def _switch_no_default_no_match() -> dict:
    """Switch with no matching case and no default — nothing executes."""
    return {
        "version": "coreil-1.10",
        "body": [
            {
                "type": "Let",
                "name": "x",
                "value": {"type": "Literal", "value": 42},
            },
            {
                "type": "Switch",
                "test": {"type": "Var", "name": "x"},
                "cases": [
                    {
                        "value": {"type": "Literal", "value": 1},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "nope"}]}],
                    },
                ],
            },
            {"type": "Print", "args": [{"type": "Literal", "value": "done"}]},
        ],
    }


def _switch_string_cases() -> dict:
    """Switch on string values."""
    return {
        "version": "coreil-1.10",
        "body": [
            {
                "type": "Let",
                "name": "color",
                "value": {"type": "Literal", "value": "green"},
            },
            {
                "type": "Switch",
                "test": {"type": "Var", "name": "color"},
                "cases": [
                    {
                        "value": {"type": "Literal", "value": "red"},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "stop"}]}],
                    },
                    {
                        "value": {"type": "Literal", "value": "green"},
                        "body": [{"type": "Print", "args": [{"type": "Literal", "value": "go"}]}],
                    },
                ],
                "default": [
                    {"type": "Print", "args": [{"type": "Literal", "value": "unknown"}]},
                ],
            },
        ],
    }


def _switch_with_multiple_stmts() -> dict:
    """Switch case body with multiple statements."""
    return {
        "version": "coreil-1.10",
        "body": [
            {
                "type": "Let",
                "name": "x",
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "Switch",
                "test": {"type": "Var", "name": "x"},
                "cases": [
                    {
                        "value": {"type": "Literal", "value": 1},
                        "body": [
                            {"type": "Print", "args": [{"type": "Literal", "value": "first"}]},
                            {"type": "Print", "args": [{"type": "Literal", "value": "second"}]},
                        ],
                    },
                ],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

TESTS = [
    ("switch_basic", _switch_basic, "two\n"),
    ("switch_with_default", _switch_with_default, "default\n"),
    ("switch_no_default_no_match", _switch_no_default_no_match, "done\n"),
    ("switch_string_cases", _switch_string_cases, "go\n"),
    ("switch_with_multiple_stmts", _switch_with_multiple_stmts, "first\nsecond\n"),
]


def main() -> int:
    import io
    from contextlib import redirect_stdout
    from english_compiler.coreil.interp import run_coreil

    failures = 0
    print("Running Switch-Case tests...\n")

    for name, fixture_fn, expected_output in TESTS:
        doc = fixture_fn()

        # Validate
        errors = validate_coreil(doc)
        if errors:
            print(f"  FAIL {name}: validation errors: {errors}")
            failures += 1
            continue

        # Run interpreter
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_coreil(doc)
        actual = buf.getvalue()
        if actual != expected_output:
            print(f"  FAIL {name}: expected {expected_output!r}, got {actual!r}")
            failures += 1
            continue

        # Check backend parity
        try:
            verify_backend_parity(
                doc, name,
                include_rust=False,
                include_go=False,
                include_wasm=False,
            )
        except TestFailure as exc:
            print(f"  FAIL {name}: parity error: {exc}")
            failures += 1
            continue

        print(f"  PASS {name}")

    print()
    if failures:
        print(f"{failures}/{len(TESTS)} Switch tests FAILED")
        return 1

    print(f"All {len(TESTS)} Switch-Case tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
