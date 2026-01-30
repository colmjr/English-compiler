"""Core IL runner for browser environment.

This module provides a browser-friendly API for running Core IL programs
in Pyodide. It captures stdout and returns results as JSON.
"""

import base64
import json
import sys
from io import StringIO
from typing import Any

from english_compiler.coreil import validate_coreil, run_coreil, emit_python


def _decode_b64(b64_str: str) -> str:
    """Decode a base64-encoded UTF-8 string."""
    return base64.b64decode(b64_str).decode('utf-8')


def _capture_output(func):
    """Decorator to capture stdout during function execution."""
    def wrapper(*args, **kwargs):
        old_stdout = sys.stdout
        sys.stdout = captured = StringIO()
        try:
            result = func(*args, **kwargs)
            output = captured.getvalue()
            return result, output
        finally:
            sys.stdout = old_stdout
    return wrapper


def validate(json_str: str) -> str:
    """Validate a Core IL program.

    Args:
        json_str: JSON string containing the Core IL program

    Returns:
        JSON string with validation result:
        {
            "success": bool,
            "errors": [{"path": str, "message": str}, ...]
        }
    """
    try:
        doc = json.loads(json_str)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "errors": [{"path": "$", "message": f"Invalid JSON: {e}"}]
        })

    errors = validate_coreil(doc)
    return json.dumps({
        "success": len(errors) == 0,
        "errors": errors
    })


def run(json_str: str) -> str:
    """Run a Core IL program and capture output.

    Args:
        json_str: JSON string containing the Core IL program

    Returns:
        JSON string with execution result:
        {
            "success": bool,
            "output": str,
            "error": str | null
        }
    """
    try:
        doc = json.loads(json_str)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "output": "",
            "error": f"Invalid JSON: {e}"
        })

    # Validate first
    errors = validate_coreil(doc)
    if errors:
        error_msgs = [f"{e['path']}: {e['message']}" for e in errors]
        return json.dumps({
            "success": False,
            "output": "",
            "error": "Validation errors:\n" + "\n".join(error_msgs)
        })

    # Capture stdout during execution
    old_stdout = sys.stdout
    sys.stdout = captured = StringIO()
    error_messages = []

    def error_callback(msg: str):
        error_messages.append(msg)

    try:
        exit_code = run_coreil(doc, error_callback=error_callback)
        output = captured.getvalue()

        if exit_code != 0 or error_messages:
            return json.dumps({
                "success": False,
                "output": output,
                "error": "\n".join(error_messages) if error_messages else "Runtime error"
            })

        return json.dumps({
            "success": True,
            "output": output,
            "error": None
        })
    except Exception as e:
        output = captured.getvalue()
        return json.dumps({
            "success": False,
            "output": output,
            "error": str(e)
        })
    finally:
        sys.stdout = old_stdout


def generate_python(json_str: str) -> str:
    """Generate Python code from a Core IL program.

    Args:
        json_str: JSON string containing the Core IL program

    Returns:
        JSON string with generation result:
        {
            "success": bool,
            "code": str,
            "error": str | null
        }
    """
    try:
        doc = json.loads(json_str)
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "code": "",
            "error": f"Invalid JSON: {e}"
        })

    # Validate first
    errors = validate_coreil(doc)
    if errors:
        error_msgs = [f"{e['path']}: {e['message']}" for e in errors]
        return json.dumps({
            "success": False,
            "code": "",
            "error": "Validation errors:\n" + "\n".join(error_msgs)
        })

    try:
        code = emit_python(doc)
        return json.dumps({
            "success": True,
            "code": code,
            "error": None
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "code": "",
            "error": str(e)
        })


def get_version() -> str:
    """Get Core IL version information.

    Returns:
        JSON string with version info:
        {
            "coreil_version": str,
            "package_version": str,
            "supported_versions": list[str]
        }
    """
    from english_compiler.coreil.versions import (
        COREIL_VERSION, PACKAGE_VERSION, SUPPORTED_VERSIONS
    )
    return json.dumps({
        "coreil_version": COREIL_VERSION,
        "package_version": PACKAGE_VERSION,
        "supported_versions": sorted(list(SUPPORTED_VERSIONS))
    })


# Base64 wrapper functions for safe string passing from JavaScript
def validate_b64(b64_str: str) -> str:
    """Validate a Core IL program (base64-encoded input)."""
    return validate(_decode_b64(b64_str))


def run_b64(b64_str: str) -> str:
    """Run a Core IL program (base64-encoded input)."""
    return run(_decode_b64(b64_str))


def generate_python_b64(b64_str: str) -> str:
    """Generate Python code from a Core IL program (base64-encoded input)."""
    return generate_python(_decode_b64(b64_str))
