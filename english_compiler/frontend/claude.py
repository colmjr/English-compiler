"""Claude frontend for Core IL generation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import anthropic

from english_compiler.coreil.validate import validate_coreil
from english_compiler.frontend.coreil_schema import COREIL_JSON_SCHEMA


def _load_system_prompt() -> str:
    prompt_path = Path(__file__).with_name("prompt.txt")
    return prompt_path.read_text(encoding="utf-8")


def _get_max_tokens() -> int:
    raw = os.getenv("ANTHROPIC_MAX_TOKENS", "4096")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("ANTHROPIC_MAX_TOKENS must be an integer") from exc
    if value <= 0:
        raise ValueError("ANTHROPIC_MAX_TOKENS must be positive")
    return value


def _build_user_message(source_text: str, errors: list[dict] | None) -> str:
    if not errors:
        return source_text
    return (
        f"{source_text}\n\nPrevious output failed validation. "
        f"Errors: {json.dumps(errors, sort_keys=True)}"
    )


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


def _request_coreil(
    client: anthropic.Anthropic,
    model: str,
    max_tokens: int,
    system_prompt: str,
    source_text: str,
    errors: list[dict] | None,
) -> tuple[dict, str, str]:
    user_message = _build_user_message(source_text, errors)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "coreil", "schema": COREIL_JSON_SCHEMA},
            },
        )
        raw_text = _extract_text(response)
        if not raw_text:
            raise ValueError("Claude returned an empty response")
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            snippet = raw_text[:400]
            raise ValueError(
                "Claude returned invalid JSON. "
                f"Response snippet: {snippet}"
            ) from exc
        if not isinstance(data, dict):
            raise ValueError("Claude returned JSON that is not an object")
        return data, raw_text, "structured"
    except TypeError:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            tools=[
                {
                    "name": "emit_coreil",
                    "description": "Emit Core IL JSON",
                    "input_schema": COREIL_JSON_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "emit_coreil"},
        )
        tool_input, raw_text = _extract_tool_input(response, "emit_coreil")
        if tool_input is None:
            snippet = raw_text[:400]
            raise ValueError(
                "Claude did not return tool output. "
                f"Response snippet: {snippet}"
            )
        return tool_input, raw_text, "tool"


def generate_coreil_from_text(source_text: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250514")
    max_tokens = _get_max_tokens()
    system_prompt = _load_system_prompt()

    client = anthropic.Anthropic(api_key=api_key)

    data, raw_text, method = _request_coreil(
        client, model, max_tokens, system_prompt, source_text, None
    )
    errors = validate_coreil(data)
    if errors:
        data, raw_text, method = _request_coreil(
            client, model, max_tokens, system_prompt, source_text, errors
        )
        errors = validate_coreil(data)
        if errors:
            snippet = raw_text[:400]
            raise RuntimeError(
                "Claude output failed validation after retry. "
                f"model={model} method={method} errors={errors} "
                f"snippet={snippet}"
            )

    return data
