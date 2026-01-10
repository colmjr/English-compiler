"""Tests for Core IL v1.1 string operations."""

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


def test_stringlength():
    """Test StringLength operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Print",
                "args": [
                    {
                        "type": "StringLength",
                        "base": {"type": "Literal", "value": "hello"},
                    }
                ],
            }
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "5\n"

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
    assert result.stdout == interp_output

    print("✓ test_stringlength passed")


def test_substring():
    """Test Substring operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Substring",
                        "base": {"type": "Literal", "value": "abcdef"},
                        "start": {"type": "Literal", "value": 1},
                        "end": {"type": "Literal", "value": 4},
                    }
                ],
            }
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "bcd\n"

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
    assert result.stdout == interp_output

    print("✓ test_substring passed")


def test_charat():
    """Test CharAt operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Print",
                "args": [
                    {
                        "type": "CharAt",
                        "base": {"type": "Literal", "value": "hello"},
                        "index": {"type": "Literal", "value": 1},
                    }
                ],
            }
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "e\n"

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
    assert result.stdout == interp_output

    print("✓ test_charat passed")


def test_join():
    """Test Join operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Join",
                        "sep": {"type": "Literal", "value": ", "},
                        "items": {
                            "type": "Array",
                            "items": [
                                {"type": "Literal", "value": "a"},
                                {"type": "Literal", "value": "b"},
                                {"type": "Literal", "value": "c"},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "a, b, c\n"

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
    assert result.stdout == interp_output

    print("✓ test_join passed")


def test_join_with_numbers():
    """Test Join operation with non-string items (should convert to strings)."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Join",
                        "sep": {"type": "Literal", "value": "-"},
                        "items": {
                            "type": "Array",
                            "items": [
                                {"type": "Literal", "value": 1},
                                {"type": "Literal", "value": 2},
                                {"type": "Literal", "value": 3},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()
    assert interp_output == "1-2-3\n"

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
    assert result.stdout == interp_output

    print("✓ test_join_with_numbers passed")


def main():
    """Run all string operation tests."""
    print("Testing Core IL v1.1 string operations...\n")

    test_stringlength()
    test_substring()
    test_charat()
    test_join()
    test_join_with_numbers()

    print("\nAll string operation tests passed! ✓")
    print("Verified:")
    print("  • StringLength")
    print("  • Substring (end-exclusive slicing)")
    print("  • CharAt (character access)")
    print("  • Join (with automatic string conversion)")
    print("  • Backend parity (interpreter output == Python output)")


if __name__ == "__main__":
    main()
