"""Tests for Deque operations in Core IL v1.1."""

from __future__ import annotations

import io
import subprocess
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil


def test_deque_new():
    """Test DequeNew expression."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "Print",
                "args": [{"type": "DequeSize", "base": {"type": "Var", "name": "q"}}],
            },
        ],
    }

    # Validation
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()

    # Python backend
    code = emit_python(doc)
    assert "from collections import deque" in code
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "0\n"
    assert result.stdout == interp_output


def test_pushback():
    """Test PushBack operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 3},
            },
            {
                "type": "Print",
                "args": [{"type": "DequeSize", "base": {"type": "Var", "name": "q"}}],
            },
        ],
    }

    # Validation
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()

    # Python backend
    code = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "3\n"
    assert result.stdout == interp_output


def test_pushfront():
    """Test PushFront operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "PushFront",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "PushFront",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "Print",
                "args": [{"type": "DequeSize", "base": {"type": "Var", "name": "q"}}],
            },
        ],
    }

    # Validation
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()

    # Python backend
    code = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "2\n"
    assert result.stdout == interp_output


def test_popfront():
    """Test PopFront operation (FIFO queue behavior)."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 3},
            },
            {
                "type": "PopFront",
                "base": {"type": "Var", "name": "q"},
                "target": "x",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "x"}],
            },
            {
                "type": "PopFront",
                "base": {"type": "Var", "name": "q"},
                "target": "y",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "y"}],
            },
            {
                "type": "PopFront",
                "base": {"type": "Var", "name": "q"},
                "target": "z",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "z"}],
            },
        ],
    }

    # Validation
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()

    # Python backend
    code = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "1\n2\n3\n"
    assert result.stdout == interp_output


def test_popback():
    """Test PopBack operation (LIFO stack behavior)."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "PushBack",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 3},
            },
            {
                "type": "PopBack",
                "base": {"type": "Var", "name": "q"},
                "target": "x",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "x"}],
            },
            {
                "type": "PopBack",
                "base": {"type": "Var", "name": "q"},
                "target": "y",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "y"}],
            },
            {
                "type": "PopBack",
                "base": {"type": "Var", "name": "q"},
                "target": "z",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "z"}],
            },
        ],
    }

    # Validation
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()

    # Python backend
    code = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "3\n2\n1\n"
    assert result.stdout == interp_output


def test_mixed_pushpop():
    """Test mixing PushFront and PopBack operations."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "PushFront",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "PushFront",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "PushFront",
                "base": {"type": "Var", "name": "q"},
                "value": {"type": "Literal", "value": 3},
            },
            {
                "type": "PopBack",
                "base": {"type": "Var", "name": "q"},
                "target": "x",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "x"}],
            },
            {
                "type": "PopBack",
                "base": {"type": "Var", "name": "q"},
                "target": "y",
            },
            {
                "type": "Print",
                "args": [{"type": "Var", "name": "y"}],
            },
        ],
    }

    # Validation
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    interp_output = buffer.getvalue()

    # Python backend
    code = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    # PushFront: 1, 2, 3 → deque is [3, 2, 1]
    # PopBack: removes 1, then 2
    assert interp_output == "1\n2\n"
    assert result.stdout == interp_output


def test_empty_pop_error():
    """Test that popping from empty deque raises error."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "q",
                "value": {"type": "DequeNew"},
            },
            {
                "type": "PopFront",
                "base": {"type": "Var", "name": "q"},
                "target": "x",
            },
        ],
    }

    # Validation should pass
    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    # Interpreter should raise runtime error
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 1  # Should fail at runtime


if __name__ == "__main__":
    test_deque_new()
    test_pushback()
    test_pushfront()
    test_popfront()
    test_popback()
    test_mixed_pushpop()
    test_empty_pop_error()
    print("All deque tests passed!")
