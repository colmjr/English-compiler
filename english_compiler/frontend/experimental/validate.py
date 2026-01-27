"""Syntax validation for generated code."""

from __future__ import annotations

import ast


def validate_syntax(code: str, target: str) -> list[str]:
    """Validate syntax of generated code.

    Only validates Python (using ast.parse). JS/C++ validation is skipped.

    Args:
        code: The generated source code.
        target: Target language ("python", "javascript", "cpp").

    Returns:
        List of error messages. Empty list if validation passes or is skipped.
    """
    if target == "python":
        return _validate_python(code)
    # Skip validation for JS and C++ - trust LLM output
    return []


def _validate_python(code: str) -> list[str]:
    """Validate Python syntax using ast.parse.

    Args:
        code: Python source code to validate.

    Returns:
        List of syntax errors. Empty if valid.
    """
    try:
        ast.parse(code)
        return []
    except SyntaxError as e:
        line_info = f"Line {e.lineno}" if e.lineno else "Unknown line"
        return [f"{line_info}: {e.msg}"]
