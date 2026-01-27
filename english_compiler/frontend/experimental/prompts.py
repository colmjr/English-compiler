"""Load experimental prompts for direct code generation."""

from __future__ import annotations

from pathlib import Path

_PROMPTS: dict[str, str] = {}


def get_experimental_prompt(target: str) -> str:
    """Get system prompt for direct code generation to target language.

    Args:
        target: Target language ("python", "javascript", "cpp").

    Returns:
        The system prompt for the target language.

    Raises:
        ValueError: If the target language is not supported.
    """
    if target not in ("python", "javascript", "cpp"):
        raise ValueError(f"Unsupported experimental target: {target}")

    if target not in _PROMPTS:
        prompt_path = Path(__file__).parent / f"prompt_{target}.txt"
        _PROMPTS[target] = prompt_path.read_text(encoding="utf-8")
    return _PROMPTS[target]
