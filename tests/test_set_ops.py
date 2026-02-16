"""Tests for Set operations in Core IL v1.1."""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.emit import emit_python
from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil


def test_set_literal_empty():
    """Test empty Set literal."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "s",
                "value": {"type": "Set", "items": []},
            },
            {
                "type": "Print",
                "args": [{"type": "SetSize", "base": {"type": "Var", "name": "s"}}],
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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "0\n"
    assert result.stdout == interp_output


def test_set_literal_with_items():
    """Test Set literal with items."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "s",
                "value": {
                    "type": "Set",
                    "items": [
                        {"type": "Literal", "value": 1},
                        {"type": "Literal", "value": 2},
                        {"type": "Literal", "value": 3},
                    ],
                },
            },
            {
                "type": "Print",
                "args": [{"type": "SetSize", "base": {"type": "Var", "name": "s"}}],
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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "3\n"
    assert result.stdout == interp_output


def test_sethas():
    """Test SetHas operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "s",
                "value": {
                    "type": "Set",
                    "items": [
                        {"type": "Literal", "value": 1},
                        {"type": "Literal", "value": 2},
                        {"type": "Literal", "value": 3},
                    ],
                },
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "SetHas",
                        "base": {"type": "Var", "name": "s"},
                        "value": {"type": "Literal", "value": 2},
                    }
                ],
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "SetHas",
                        "base": {"type": "Var", "name": "s"},
                        "value": {"type": "Literal", "value": 5},
                    }
                ],
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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "True\nFalse\n"
    assert result.stdout == interp_output


def test_setadd():
    """Test SetAdd operation."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "s",
                "value": {"type": "Set", "items": []},
            },
            {
                "type": "SetAdd",
                "base": {"type": "Var", "name": "s"},
                "value": {"type": "Literal", "value": 1},
            },
            {
                "type": "SetAdd",
                "base": {"type": "Var", "name": "s"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "SetAdd",
                "base": {"type": "Var", "name": "s"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "Print",
                "args": [{"type": "SetSize", "base": {"type": "Var", "name": "s"}}],
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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "2\n"
    assert result.stdout == interp_output


def test_setremove():
    """Test SetRemove operation with no-op semantics."""
    doc = {
        "version": "coreil-1.1",
        "body": [
            {
                "type": "Let",
                "name": "s",
                "value": {
                    "type": "Set",
                    "items": [
                        {"type": "Literal", "value": 1},
                        {"type": "Literal", "value": 2},
                        {"type": "Literal", "value": 3},
                    ],
                },
            },
            {
                "type": "SetRemove",
                "base": {"type": "Var", "name": "s"},
                "value": {"type": "Literal", "value": 2},
            },
            {
                "type": "SetRemove",
                "base": {"type": "Var", "name": "s"},
                "value": {"type": "Literal", "value": 5},
            },
            {
                "type": "Print",
                "args": [{"type": "SetSize", "base": {"type": "Var", "name": "s"}}],
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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "2\n"
    assert result.stdout == interp_output


def test_dedup():
    """Test deduplication using Set."""
    doc = json.load(
        open("examples/dedup_demo.coreil.json", encoding="utf-8")
    )

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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "3\n"
    assert result.stdout == interp_output


def test_two_sum():
    """Test two-sum problem using Set."""
    doc = json.load(
        open("examples/two_sum_demo.coreil.json", encoding="utf-8")
    )

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
    code, _ = emit_python(doc)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()
        result = subprocess.run(
            ["python", f.name], capture_output=True, text=True, check=True
        )
        Path(f.name).unlink()

    assert interp_output == "True\n"
    assert result.stdout == interp_output
