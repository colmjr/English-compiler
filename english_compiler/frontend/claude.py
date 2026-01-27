"""Claude frontend for Core IL generation."""

from __future__ import annotations

import os
from typing import Any

from english_compiler.frontend.base import BaseFrontend, get_env_int, get_required_env


def _extract_text(response: Any) -> str:
    text_parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if isinstance(text, str):
            text_parts.append(text)
    return "".join(text_parts).strip()


def _extract_tool_input(response: Any, tool_name: str) -> tuple[dict | None, str]:
    raw_text = _extract_text(response)
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type is None and isinstance(block, dict):
            block_type = block.get("type")
        if block_type == "tool_use":
            name = getattr(block, "name", None)
            tool_input = getattr(block, "input", None)
            if isinstance(block, dict):
                name = block.get("name", name)
                tool_input = block.get("input", tool_input)
            if name == tool_name and isinstance(tool_input, dict):
                return tool_input, raw_text
    return None, raw_text


def _strip_markdown_code_block(text: str) -> str:
    """Strip markdown code block markers from text."""
    text = text.strip()
    # Handle ```python, ```javascript, ```cpp, etc.
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class ClaudeFrontend(BaseFrontend):
    """Claude API frontend using Anthropic SDK."""

    def __init__(self) -> None:
        super().__init__()
        api_key = get_required_env("ANTHROPIC_API_KEY")

        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "Anthropic SDK not installed. Run: pip install anthropic"
            ) from exc

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
        self.max_tokens = get_env_int("ANTHROPIC_MAX_TOKENS", 4096, min_value=1)

    def get_model_name(self) -> str:
        return self.model

    def _call_api(self, user_message: str) -> dict:
        """Call Claude API with structured output or tool fallback."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "coreil", "schema": self.schema},
                },
            )
            raw_text = _extract_text(response)
            return self._parse_json_response(raw_text, "Claude")
        except TypeError:
            # Fall back to tool use for older models
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0,
                system=self.system_prompt,
                messages=[{"role": "user", "content": user_message}],
                tools=[
                    {
                        "name": "emit_coreil",
                        "description": "Emit Core IL JSON",
                        "input_schema": self.schema,
                    }
                ],
                tool_choice={"type": "tool", "name": "emit_coreil"},
            )
            tool_input, raw_text = _extract_tool_input(response, "emit_coreil")
            if tool_input is None:
                snippet = raw_text[:400]
                raise ValueError(
                    f"Claude did not return tool output. Response snippet: {snippet}"
                )
            return tool_input

    def _call_api_text(self, user_message: str, system_prompt: str) -> str:
        """Call Claude API for plain text response (experimental mode)."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        text = _extract_text(response)
        return _strip_markdown_code_block(text)
