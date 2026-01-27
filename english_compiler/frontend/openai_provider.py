"""OpenAI frontend for Core IL generation."""

from __future__ import annotations

import os

from english_compiler.frontend.base import BaseFrontend, get_env_int, get_required_env


class OpenAIFrontend(BaseFrontend):
    """OpenAI API frontend using the OpenAI SDK."""

    def __init__(self) -> None:
        super().__init__()
        api_key = get_required_env("OPENAI_API_KEY")

        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK not installed. Run: pip install openai"
            ) from exc

        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.max_tokens = get_env_int("OPENAI_MAX_TOKENS", 4096, min_value=1)

    def get_model_name(self) -> str:
        return self.model

    def _call_api(self, user_message: str) -> dict:
        """Call OpenAI API with JSON mode."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content
        return self._parse_json_response(raw_text, "OpenAI")

    def _call_api_text(self, user_message: str, system_prompt: str) -> str:
        """Call OpenAI API for plain text response (experimental mode)."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        text = response.choices[0].message.content or ""
        return _strip_markdown_code_block(text)


def _strip_markdown_code_block(text: str) -> str:
    """Strip markdown code block markers from text."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
