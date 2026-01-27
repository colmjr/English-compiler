"""Experimental direct compilation mode.

This module provides functionality for compiling English directly to target
languages (Python, JavaScript, C++) without going through Core IL.

WARNING: This mode is NON-DETERMINISTIC and should not be used in production.
"""

from english_compiler.frontend.experimental.prompts import get_experimental_prompt
from english_compiler.frontend.experimental.validate import validate_syntax

__all__ = ["get_experimental_prompt", "validate_syntax"]
