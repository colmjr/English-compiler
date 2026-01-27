"""Abstract base class for LLM frontends."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from english_compiler.coreil.validate import validate_coreil
from english_compiler.frontend.coreil_schema import COREIL_JSON_SCHEMA


def get_env_int(name: str, default: int, *, min_value: int | None = None) -> int:
    """Get an integer from an environment variable with validation.

    Args:
        name: Environment variable name.
        default: Default value if not set.
        min_value: Optional minimum allowed value.

    Returns:
        The parsed integer value.

    Raises:
        ValueError: If the value is not a valid integer or below min_value.
    """
    raw = os.getenv(name)
    if raw is None:
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got: {raw!r}") from exc

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be at least {min_value}, got: {value}")

    return value


def get_required_env(name: str) -> str:
    """Get a required environment variable.

    Args:
        name: Environment variable name.

    Returns:
        The environment variable value.

    Raises:
        RuntimeError: If the environment variable is not set.
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def _load_system_prompt() -> str:
    """Load the shared system prompt from prompt.txt."""
    prompt_path = Path(__file__).with_name("prompt.txt")
    return prompt_path.read_text(encoding="utf-8")


def _build_user_message(source_text: str, errors: list[dict] | None) -> str:
    """Build user message, optionally including validation errors for retry."""
    if not errors:
        return source_text
    return (
        f"{source_text}\n\nPrevious output failed validation. "
        f"Errors: {json.dumps(errors, sort_keys=True)}"
    )


class BaseFrontend(ABC):
    """Abstract base class for LLM frontends.

    Provides shared logic for:
    - Loading the system prompt
    - Building user messages with error feedback
    - JSON response parsing
    - Validation and retry flow
    """

    def __init__(self) -> None:
        self.system_prompt = _load_system_prompt()
        self.schema = COREIL_JSON_SCHEMA

    def _parse_json_response(
        self,
        raw_text: str | None,
        provider_name: str,
        *,
        strip_markdown: bool = False,
    ) -> dict:
        """Parse JSON from LLM response with standard error handling.

        Args:
            raw_text: The raw text response from the LLM.
            provider_name: Name of the provider for error messages (e.g., "Claude", "OpenAI").
            strip_markdown: If True, strip markdown code block markers before parsing.

        Returns:
            Parsed JSON as a dict.

        Raises:
            ValueError: If the response is empty, not valid JSON, or not an object.
        """
        if not raw_text:
            raise ValueError(f"{provider_name} returned an empty response")

        text = raw_text
        if strip_markdown:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            snippet = raw_text[:400]
            raise ValueError(
                f"{provider_name} returned invalid JSON. Response snippet: {snippet}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(f"{provider_name} returned JSON that is not an object")

        return data

    @abstractmethod
    def _call_api(self, user_message: str) -> dict:
        """Provider-specific API call.

        Args:
            user_message: The user message to send to the LLM.

        Returns:
            Parsed JSON dict containing the Core IL program.

        Raises:
            ValueError: If the API returns invalid JSON or an empty response.
            RuntimeError: If the API call fails.
        """
        pass

    @abstractmethod
    def _call_api_text(self, user_message: str, system_prompt: str) -> str:
        """Call API expecting plain text response (for experimental mode).

        Args:
            user_message: The user message to send.
            system_prompt: The system prompt to use.

        Returns:
            Raw text response from the LLM.

        Raises:
            RuntimeError: If the API call fails.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier for logging."""
        pass

    def generate_code_direct(self, source_text: str, target: str) -> str:
        """Generate target code directly without Core IL (EXPERIMENTAL).

        This method bypasses Core IL and generates code directly from English.
        The output is non-deterministic and may contain bugs.

        Args:
            source_text: The English description to compile.
            target: Target language ("python", "javascript", "cpp").

        Returns:
            Generated source code as a string.

        Raises:
            ValueError: If the target is not supported.
            RuntimeError: If the API call fails.
        """
        from english_compiler.frontend.experimental import get_experimental_prompt

        prompt = get_experimental_prompt(target)
        return self._call_api_text(source_text, prompt)

    def generate_coreil_from_text(self, source_text: str) -> dict:
        """Generate Core IL from source text with validation and retry.

        Args:
            source_text: The English pseudocode to compile.

        Returns:
            Validated Core IL program as a dict.

        Raises:
            RuntimeError: If validation fails after retry.
        """
        user_message = _build_user_message(source_text, None)
        data = self._call_api(user_message)
        errors = validate_coreil(data)

        if errors:
            retry_message = _build_user_message(source_text, errors)
            data = self._call_api(retry_message)
            errors = validate_coreil(data)
            if errors:
                raise RuntimeError(
                    f"Validation failed after retry. "
                    f"model={self.get_model_name()} errors={errors}"
                )

        return data
