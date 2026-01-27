"""Frontend package for LLM-based Core IL generation.

Provides a factory function to get the appropriate frontend based on name
or auto-detect based on available environment variables.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from english_compiler.frontend.base import BaseFrontend


# Provider detection order for auto-detection
_PROVIDER_ENV_VARS = [
    ("claude", "ANTHROPIC_API_KEY"),
    ("openai", "OPENAI_API_KEY"),
    ("gemini", "GEMINI_API_KEY"),
    ("qwen", "QWEN_API_KEY"),
]


def get_frontend(name: str | None = None) -> "BaseFrontend":
    """Get a frontend instance by name or auto-detect.

    Args:
        name: Frontend name ("claude", "openai", "gemini", "qwen", "mock")
              or None for auto-detection.

    Returns:
        A frontend instance.

    Raises:
        ValueError: If the frontend name is invalid.
        RuntimeError: If the required API key is not set.
    """
    if name is None:
        name = _auto_detect_provider()

    if name == "mock":
        from english_compiler.frontend.mock_llm import MockFrontend
        return MockFrontend()
    elif name == "claude":
        from english_compiler.frontend.claude import ClaudeFrontend
        return ClaudeFrontend()
    elif name == "openai":
        from english_compiler.frontend.openai_provider import OpenAIFrontend
        return OpenAIFrontend()
    elif name == "gemini":
        from english_compiler.frontend.gemini import GeminiFrontend
        return GeminiFrontend()
    elif name == "qwen":
        from english_compiler.frontend.qwen import QwenFrontend
        return QwenFrontend()
    else:
        raise ValueError(f"Unknown frontend: {name}")


def _auto_detect_provider() -> str:
    """Auto-detect available provider based on environment variables.

    Returns:
        Provider name, or "mock" if no API keys are set.
    """
    for provider, env_var in _PROVIDER_ENV_VARS:
        if os.getenv(env_var):
            return provider
    return "mock"


def list_available_frontends() -> list[str]:
    """List all available frontend names.

    Returns:
        List of frontend names that have their API keys configured,
        plus "mock" which is always available.
    """
    available = ["mock"]
    for provider, env_var in _PROVIDER_ENV_VARS:
        if os.getenv(env_var):
            available.append(provider)
    return available


def generate_coreil_from_text(source_text: str, provider: str | None = None) -> dict:
    """Generate Core IL from source text.

    This is a convenience function that creates a frontend instance
    and calls its generate_coreil_from_text method.

    Args:
        source_text: The English/pseudocode source text to compile.
        provider: Frontend provider name ("claude", "openai", "gemini", "qwen", "mock")
                  or None for auto-detection.

    Returns:
        The generated Core IL as a dictionary.
    """
    frontend = get_frontend(provider)
    return frontend.generate_coreil_from_text(source_text)
