"""Abstract base class for LLM frontends."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from english_compiler.coreil.validate import validate_coreil
from english_compiler.frontend.coreil_schema import COREIL_JSON_SCHEMA


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

    def _parse_json_response(self, raw_text: str | None, provider_name: str) -> dict:
        """Parse JSON from LLM response with standard error handling.

        Args:
            raw_text: The raw text response from the LLM.
            provider_name: Name of the provider for error messages (e.g., "Claude", "OpenAI").

        Returns:
            Parsed JSON as a dict.

        Raises:
            ValueError: If the response is empty, not valid JSON, or not an object.
        """
        if not raw_text:
            raise ValueError(f"{provider_name} returned an empty response")

        try:
            data = json.loads(raw_text)
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
    def get_model_name(self) -> str:
        """Return the model identifier for logging."""
        pass

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
