"""Tests for Core IL v1.1 Record support."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil


def test_record_basic():
    """Test basic Record creation and field access."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "point",
                "value": {
                    "type": "Record",
                    "fields": [
                        {"name": "x", "value": {"type": "Literal", "value": 2}},
                        {"name": "y", "value": {"type": "Literal", "value": 3}},
                    ],
                },
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "GetField",
                        "base": {"type": "Var", "name": "point"},
                        "name": "x",
                    }
                ],
            },
        ],
    }

    # Validate
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Test interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "2\n"

    # Test Python backend
    python_code = emit_python(doc)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(python_code)
        tmp_path = tmp.name

    result = subprocess.run(
        [sys.executable, tmp_path], capture_output=True, text=True, timeout=5
    )
    Path(tmp_path).unlink()

    assert result.returncode == 0
    python_output = result.stdout
    assert python_output == interp_output, f"Backend mismatch: {python_output!r} != {interp_output!r}"

    print("✓ test_record_basic passed")


def test_record_setfield():
    """Test SetField mutation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "point",
                "value": {
                    "type": "Record",
                    "fields": [
                        {"name": "x", "value": {"type": "Literal", "value": 2}},
                        {"name": "y", "value": {"type": "Literal", "value": 3}},
                    ],
                },
            },
            {
                "type": "SetField",
                "base": {"type": "Var", "name": "point"},
                "name": "x",
                "value": {"type": "Literal", "value": 10},
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "GetField",
                        "base": {"type": "Var", "name": "point"},
                        "name": "x",
                    }
                ],
            },
        ],
    }

    # Validate
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Test interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "10\n"

    # Test Python backend
    python_code = emit_python(doc)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(python_code)
        tmp_path = tmp.name

    result = subprocess.run(
        [sys.executable, tmp_path], capture_output=True, text=True, timeout=5
    )
    Path(tmp_path).unlink()

    assert result.returncode == 0
    python_output = result.stdout
    assert python_output == interp_output, f"Backend mismatch: {python_output!r} != {interp_output!r}"

    print("✓ test_record_setfield passed")


def test_record_arithmetic():
    """Test arithmetic with record fields."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "point",
                "value": {
                    "type": "Record",
                    "fields": [
                        {"name": "x", "value": {"type": "Literal", "value": 5}},
                        {"name": "y", "value": {"type": "Literal", "value": 7}},
                    ],
                },
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Binary",
                        "op": "+",
                        "left": {
                            "type": "GetField",
                            "base": {"type": "Var", "name": "point"},
                            "name": "x",
                        },
                        "right": {
                            "type": "GetField",
                            "base": {"type": "Var", "name": "point"},
                            "name": "y",
                        },
                    }
                ],
            },
        ],
    }

    # Validate
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Test interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "12\n"

    # Test Python backend
    python_code = emit_python(doc)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(python_code)
        tmp_path = tmp.name

    result = subprocess.run(
        [sys.executable, tmp_path], capture_output=True, text=True, timeout=5
    )
    Path(tmp_path).unlink()

    assert result.returncode == 0
    python_output = result.stdout
    assert python_output == interp_output, f"Backend mismatch: {python_output!r} != {interp_output!r}"

    print("✓ test_record_arithmetic passed")


def test_record_nested():
    """Test nested records."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "rect",
                "value": {
                    "type": "Record",
                    "fields": [
                        {
                            "name": "topleft",
                            "value": {
                                "type": "Record",
                                "fields": [
                                    {"name": "x", "value": {"type": "Literal", "value": 0}},
                                    {"name": "y", "value": {"type": "Literal", "value": 0}},
                                ],
                            },
                        },
                        {
                            "name": "bottomright",
                            "value": {
                                "type": "Record",
                                "fields": [
                                    {"name": "x", "value": {"type": "Literal", "value": 10}},
                                    {"name": "y", "value": {"type": "Literal", "value": 20}},
                                ],
                            },
                        },
                    ],
                },
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "GetField",
                        "base": {
                            "type": "GetField",
                            "base": {"type": "Var", "name": "rect"},
                            "name": "bottomright",
                        },
                        "name": "x",
                    }
                ],
            },
        ],
    }

    # Validate
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Test interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "10\n"

    # Test Python backend
    python_code = emit_python(doc)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(python_code)
        tmp_path = tmp.name

    result = subprocess.run(
        [sys.executable, tmp_path], capture_output=True, text=True, timeout=5
    )
    Path(tmp_path).unlink()

    assert result.returncode == 0
    python_output = result.stdout
    assert python_output == interp_output, f"Backend mismatch: {python_output!r} != {interp_output!r}"

    print("✓ test_record_nested passed")


def main():
    """Run all Record tests."""
    print("Testing Core IL v1.1 Record support...\n")

    test_record_basic()
    test_record_setfield()
    test_record_arithmetic()
    test_record_nested()

    print("\nAll Record tests passed! ✓")
    print("Verified:")
    print("  • Record creation and field access")
    print("  • SetField mutation")
    print("  • Arithmetic with record fields")
    print("  • Nested records")
    print("  • Backend parity (interpreter output == Python output)")


if __name__ == "__main__":
    main()
