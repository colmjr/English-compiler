"""Tests for the --explain-errors feature."""

from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

from english_compiler.coreil.interp import run_coreil
from english_compiler.frontend.error_explainer import explain_error, _load_error_prompt
from english_compiler.frontend.mock_llm import MockFrontend


def test_error_callback_is_called():
    """Test that error_callback is called when an error occurs."""
    # Create a Core IL program that will fail (index out of range)
    doc = {
        "version": "coreil-1.6",
        "body": [
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": []}},
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Index",
                        "base": {"type": "Var", "name": "arr"},
                        "index": {"type": "Literal", "value": 0},
                    }
                ],
            },
        ],
    }

    # Track callback invocation
    callback_messages = []

    def callback(msg: str) -> None:
        callback_messages.append(msg)

    # Run with error callback
    result = run_coreil(doc, error_callback=callback)

    assert result == 1, "Expected exit code 1 for error"
    assert len(callback_messages) == 1, "Expected exactly one error callback"
    assert "Index out of range" in callback_messages[0], f"Expected index error, got: {callback_messages[0]}"


def test_error_callback_not_called_on_success():
    """Test that error_callback is not called on successful execution."""
    doc = {
        "version": "coreil-1.6",
        "body": [
            {
                "type": "Print",
                "args": [{"type": "Literal", "value": "hello"}],
            }
        ],
    }

    callback_messages = []

    def callback(msg: str) -> None:
        callback_messages.append(msg)

    result = run_coreil(doc, error_callback=callback)

    assert result == 0, "Expected exit code 0 for success"
    assert len(callback_messages) == 0, "Expected no error callbacks on success"


def test_explain_error_with_mock_frontend():
    """Test that explain_error returns an explanation from the mock frontend."""
    frontend = MockFrontend()
    error_msg = "runtime error: Index out of range"

    explanation = explain_error(frontend, error_msg)

    # Mock frontend returns a simple explanation
    assert "error" in explanation.lower(), f"Expected 'error' in explanation: {explanation}"


def test_load_error_prompt():
    """Test that the error prompt file loads correctly."""
    prompt = _load_error_prompt()

    assert "explain" in prompt.lower(), "Expected 'explain' in prompt"
    assert "error" in prompt.lower(), "Expected 'error' in prompt"


def test_default_behavior_without_callback():
    """Test that errors are printed normally without callback."""
    doc = {
        "version": "coreil-1.6",
        "body": [
            {"type": "Let", "name": "arr", "value": {"type": "Array", "items": []}},
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Index",
                        "base": {"type": "Var", "name": "arr"},
                        "index": {"type": "Literal", "value": 0},
                    }
                ],
            },
        ],
    }

    # Capture stdout
    captured = io.StringIO()
    with mock.patch.object(sys, 'stdout', captured):
        result = run_coreil(doc)

    assert result == 1
    output = captured.getvalue()
    assert "runtime error" in output, f"Expected 'runtime error' in output: {output}"


def run_tests():
    """Run all tests and report results."""
    tests = [
        test_error_callback_is_called,
        test_error_callback_not_called_on_success,
        test_explain_error_with_mock_frontend,
        test_load_error_prompt,
        test_default_behavior_without_callback,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"  {test.__name__}: PASSED")
            passed += 1
        except AssertionError as e:
            print(f"  {test.__name__}: FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"  {test.__name__}: ERROR - {e}")
            failed += 1

    print()
    if failed == 0:
        print(f"All {passed} tests passed!")
        return 0
    else:
        print(f"{failed} test(s) failed, {passed} passed")
        return 1


if __name__ == "__main__":
    print("Running explain-errors tests...")
    print()
    raise SystemExit(run_tests())
