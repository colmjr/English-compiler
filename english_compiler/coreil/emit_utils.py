"""Shared utilities for Core IL code generation backends.

This module contains common helper functions used by all emit backends
(Python, JavaScript, C++) to avoid code duplication.
"""

from __future__ import annotations


def escape_string_literal(value: str) -> str:
    """Escape special characters for code generation.

    Handles common escape sequences for string literals across
    Python, JavaScript, and C++ backends.

    Args:
        value: The raw string value to escape

    Returns:
        The escaped string (without surrounding quotes)
    """
    return (value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t"))
