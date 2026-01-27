"""Shared utilities for Core IL code generation backends.

This module contains common helper functions used by all emit backends
(Python, JavaScript, C++) to avoid code duplication, as well as utilities
used by the interpreter.
"""

from __future__ import annotations

import re


def parse_regex_flags(flags_str: str) -> int:
    """Convert Core IL regex flags string to Python re flags.

    Supported flags:
    - 'i': Case-insensitive matching (re.IGNORECASE)
    - 'm': Multiline mode (re.MULTILINE)
    - 's': Dotall mode - dot matches newlines (re.DOTALL)

    Args:
        flags_str: A string containing flag characters, e.g. "im"

    Returns:
        Combined Python re flags integer
    """
    flags = 0
    if flags_str:
        if 'i' in flags_str:
            flags |= re.IGNORECASE
        if 'm' in flags_str:
            flags |= re.MULTILINE
        if 's' in flags_str:
            flags |= re.DOTALL
    return flags


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
