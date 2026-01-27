"""LLM-powered error explanation module.

This module provides functionality to explain runtime errors in user-friendly
terms by passing them through an LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from english_compiler.frontend.base import BaseFrontend

_ERROR_PROMPT: str | None = None


def _load_error_prompt() -> str:
    """Load and cache the error explanation prompt."""
    global _ERROR_PROMPT
    if _ERROR_PROMPT is None:
        prompt_path = Path(__file__).with_name("prompt_error.txt")
        _ERROR_PROMPT = prompt_path.read_text(encoding="utf-8")
    return _ERROR_PROMPT


def explain_error(
    frontend: BaseFrontend,
    error_message: str,
    source_text: str | None = None,
) -> str:
    """Call the LLM to explain an error in user-friendly terms.

    Args:
        frontend: The LLM frontend to use for generating the explanation.
        error_message: The raw error message from the interpreter.
        source_text: Optional source code that caused the error.

    Returns:
        A user-friendly explanation of the error.
        If the LLM call fails, returns the original error message.
    """
    prompt = _load_error_prompt()

    # Build the user message
    user_message = f"Error: {error_message}"
    if source_text:
        user_message += f"\n\nSource:\n{source_text}"

    try:
        explanation = frontend._call_api_text(user_message, prompt)
        return explanation.strip()
    except Exception:
        # On any failure, fall back to the original error
        return error_message
