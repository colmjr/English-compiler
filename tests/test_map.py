"""Tests for Core IL map operations."""

from __future__ import annotations

import io
from contextlib import redirect_stdout

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.validate import validate_coreil


def test_map_creation() -> None:
    """Test creating a map with initial values."""
    doc = {
        "version": "coreil-0.4",
        "body": [
            {
                "type": "Let",
                "name": "m",
                "value": {
                    "type": "Map",
                    "items": [
                        {
                            "key": {"type": "Literal", "value": "x"},
                            "value": {"type": "Literal", "value": 10},
                        },
                        {
                            "key": {"type": "Literal", "value": "y"},
                            "value": {"type": "Literal", "value": 20},
                        },
                    ],
                },
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Get",
                        "base": {"type": "Var", "name": "m"},
                        "key": {"type": "Literal", "value": "x"},
                    }
                ],
            },
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    assert buffer.getvalue() == "10\n"


def test_map_set() -> None:
    """Test setting a value in a map."""
    doc = {
        "version": "coreil-0.4",
        "body": [
            {
                "type": "Let",
                "name": "m",
                "value": {"type": "Map", "items": []},
            },
            {
                "type": "Set",
                "base": {"type": "Var", "name": "m"},
                "key": {"type": "Literal", "value": "key1"},
                "value": {"type": "Literal", "value": 42},
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Get",
                        "base": {"type": "Var", "name": "m"},
                        "key": {"type": "Literal", "value": "key1"},
                    }
                ],
            },
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    assert buffer.getvalue() == "42\n"


def test_map_get_missing_key() -> None:
    """Test getting a missing key returns None."""
    doc = {
        "version": "coreil-0.4",
        "body": [
            {
                "type": "Let",
                "name": "m",
                "value": {"type": "Map", "items": []},
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Get",
                        "base": {"type": "Var", "name": "m"},
                        "key": {"type": "Literal", "value": "missing"},
                    }
                ],
            },
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    assert buffer.getvalue() == "None\n"


def test_map_integer_keys() -> None:
    """Test using integer keys in a map."""
    doc = {
        "version": "coreil-0.4",
        "body": [
            {
                "type": "Let",
                "name": "m",
                "value": {
                    "type": "Map",
                    "items": [
                        {
                            "key": {"type": "Literal", "value": 1},
                            "value": {"type": "Literal", "value": "one"},
                        },
                        {
                            "key": {"type": "Literal", "value": 2},
                            "value": {"type": "Literal", "value": "two"},
                        },
                    ],
                },
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Get",
                        "base": {"type": "Var", "name": "m"},
                        "key": {"type": "Literal", "value": 2},
                    }
                ],
            },
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    assert buffer.getvalue() == "two\n"


def test_map_update_existing_key() -> None:
    """Test updating an existing key in a map."""
    doc = {
        "version": "coreil-0.4",
        "body": [
            {
                "type": "Let",
                "name": "m",
                "value": {
                    "type": "Map",
                    "items": [
                        {
                            "key": {"type": "Literal", "value": "x"},
                            "value": {"type": "Literal", "value": 100},
                        }
                    ],
                },
            },
            {
                "type": "Set",
                "base": {"type": "Var", "name": "m"},
                "key": {"type": "Literal", "value": "x"},
                "value": {"type": "Literal", "value": 200},
            },
            {
                "type": "Print",
                "args": [
                    {
                        "type": "Get",
                        "base": {"type": "Var", "name": "m"},
                        "key": {"type": "Literal", "value": "x"},
                    }
                ],
            },
        ],
    }

    errors = validate_coreil(doc)
    assert not errors, f"Validation failed: {errors}"

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        exit_code = run_coreil(doc)
    assert exit_code == 0
    assert buffer.getvalue() == "200\n"


def main() -> None:
    test_map_creation()
    test_map_set()
    test_map_get_missing_key()
    test_map_integer_keys()
    test_map_update_existing_key()
    print("All map tests passed.")


if __name__ == "__main__":
    main()
