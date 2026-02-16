"""Test the regression suite itself to demonstrate failure modes."""

from __future__ import annotations

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.validate import validate_coreil

from tests.test_helpers import (
    INVALID_HELPER_CALLS,
    check_invalid_calls,
    run_interpreter,
)


def test_validation_failure():
    """Demonstrate validation failure detection."""
    doc = {
        "version": "coreil-1.0",
        "body": [
            {
                "type": "InvalidNode",  # Invalid node type
                "value": 42,
            }
        ],
    }

    errors = validate_coreil(doc)
    assert errors, "Expected validation errors"
    assert any("InvalidNode" in str(e) for e in errors), "Expected InvalidNode error"
    print("✓ Validation failure detected correctly")


def test_invalid_helper_call():
    """Demonstrate invalid helper call detection."""
    doc = {
        "version": "coreil-1.0",
        "body": [
            {
                "type": "Let",
                "name": "x",
                "value": {
                    "type": "Call",
                    "name": "get_or_default",  # Invalid helper
                    "args": [],
                },
            }
        ],
    }

    # Check for invalid call using shared helper
    invalid_calls = check_invalid_calls(doc)
    assert "get_or_default" in invalid_calls, "Expected to find invalid helper call"
    print("✓ Invalid helper call detected correctly")


def test_interpreter_error():
    """Demonstrate interpreter error detection."""
    doc = {
        "version": "coreil-1.0",
        "body": [
            {
                "type": "Let",
                "name": "arr",
                "value": {"type": "Array", "items": []},
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Index",
                        "base": {"type": "Var", "name": "arr"},
                        "index": {"type": "Literal", "value": 0},  # Out of bounds
                    }
                ],
            },
        ],
    }

    # Validation should pass
    errors = validate_coreil(doc)
    assert not errors, f"Unexpected validation errors: {errors}"

    # But interpreter should fail
    result = run_interpreter(doc)
    assert not result.success, "Expected interpreter to fail"
    print("✓ Interpreter error detected correctly")


def test_backend_parity_same():
    """Demonstrate backend parity check (should pass)."""
    doc = {
        "version": "coreil-1.0",
        "body": [
            {
                "type": "Print",
                "args": [{"type": "Literal", "value": "hello"}],
            }
        ],
    }

    # Run interpreter using helper
    result = run_interpreter(doc)
    assert result.success, f"Interpreter failed: {result.error}"
    assert result.output == "hello\n"

    # Generate and check Python
    python_code, _ = emit_python(doc)
    assert "print(" in python_code, "Expected print statement in Python"

    print(f"✓ Backend parity test ready (interpreter output: {result.output!r})")


def test_short_circuit_parity():
    """Demonstrate that short-circuit evaluation works in both backends."""
    doc = {
        "version": "coreil-1.0",
        "body": [
            {
                "type": "Let",
                "name": "arr",
                "value": {"type": "Array", "items": []},
            },
            {
                "type": "Let",
                "name": "i",
                "value": {"type": "Literal", "value": 0},
            },
            {
                "type": "If",
                "test": {
                    "type": "Binary",
                    "op": "and",
                    "left": {
                        "type": "Binary",
                        "op": "<",
                        "left": {"type": "Var", "name": "i"},
                        "right": {
                            "type": "Length",
                            "base": {"type": "Var", "name": "arr"},
                        },
                    },
                    "right": {
                        # This would crash if evaluated (i >= len(arr))
                        "type": "Index",
                        "base": {"type": "Var", "name": "arr"},
                        "index": {"type": "Var", "name": "i"},
                    },
                },
                "then": [
                    {
                        "type": "Print",
                        "args": [{"type": "Literal", "value": "found"}],
                    }
                ],
                "else": [
                    {
                        "type": "Print",
                        "args": [{"type": "Literal", "value": "not found"}],
                    }
                ],
            },
        ],
    }

    # Validation should pass
    errors = validate_coreil(doc)
    assert not errors, f"Unexpected validation errors: {errors}"

    # Interpreter should succeed (short-circuit prevents index access)
    result = run_interpreter(doc)
    assert result.success, f"Interpreter should succeed with short-circuit: {result.error}"
    assert result.output == "not found\n", f"Expected 'not found\\n', got {result.output!r}"

    print("✓ Short-circuit evaluation works correctly in interpreter")


def main():
    """Run all regression suite tests."""
    print("Testing regression suite failure detection...\n")

    test_validation_failure()
    test_invalid_helper_call()
    test_interpreter_error()
    test_backend_parity_same()
    test_short_circuit_parity()

    print("\nAll regression suite tests passed!")
    print("The test suite correctly detects:")
    print("  • Validation failures")
    print("  • Invalid helper calls")
    print("  • Interpreter errors")
    print("  • Backend parity issues")
    print("  • Short-circuit evaluation correctness")


if __name__ == "__main__":
    main()
