"""Claude frontend for Core IL generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

import anthropic


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


def generate_coreil_from_text(source_text: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    max_tokens = _get_max_tokens()
    system_prompt = _load_system_prompt()

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": source_text}],
    )

    text_parts = []
    for block in response.content:
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if isinstance(text, str):
            text_parts.append(text)

    raw_text = "".join(text_parts).strip()
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

    return data
