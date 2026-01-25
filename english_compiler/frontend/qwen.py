"""Qwen frontend for Core IL generation."""

from __future__ import annotations

import json
import os

from english_compiler.frontend.base import BaseFrontend


class QwenFrontend(BaseFrontend):
    """Qwen API frontend using DashScope or OpenAI-compatible endpoint.

    Supports two modes:
    1. DashScope SDK (default): Uses Alibaba Cloud's dashscope library
    2. OpenAI-compatible: Set QWEN_BASE_URL to use OpenAI SDK with Qwen endpoint
    """

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key:
            raise RuntimeError("QWEN_API_KEY is not set")

        self.model = os.getenv("QWEN_MODEL", "qwen-turbo")
        self.max_tokens = int(os.getenv("QWEN_MAX_TOKENS", "4096"))
        self._base_url = os.getenv("QWEN_BASE_URL")

        if self._base_url:
            # Use OpenAI-compatible endpoint
            try:
                import openai
            except ImportError as exc:
                raise RuntimeError(
                    "OpenAI SDK not installed. Run: pip install openai"
                ) from exc
            self._client = openai.OpenAI(api_key=api_key, base_url=self._base_url)
            self._use_dashscope = False
        else:
            # Use DashScope SDK
            try:
                import dashscope
            except ImportError as exc:
                raise RuntimeError(
                    "DashScope SDK not installed. Run: pip install dashscope"
                ) from exc
            dashscope.api_key = api_key
            self._dashscope = dashscope
            self._use_dashscope = True

    def get_model_name(self) -> str:
        return self.model

    def _call_api(self, user_message: str) -> dict:
        """Call Qwen API via DashScope or OpenAI-compatible endpoint."""
        if self._use_dashscope:
            return self._call_dashscope(user_message)
        else:
            return self._call_openai_compatible(user_message)

    def _call_dashscope(self, user_message: str) -> dict:
        """Call Qwen via DashScope SDK."""
        from dashscope import Generation

        response = Generation.call(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            result_format="message",
            max_tokens=self.max_tokens,
            temperature=0,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"DashScope API error: {response.code} - {response.message}"
            )

        raw_text = response.output.choices[0].message.content
        if not raw_text:
            raise ValueError("Qwen returned an empty response")

        return self._parse_json(raw_text)

    def _call_openai_compatible(self, user_message: str) -> dict:
        """Call Qwen via OpenAI-compatible endpoint."""
        response = self._client.chat.completions.create(
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
        if not raw_text:
            raise ValueError("Qwen returned an empty response")

        return self._parse_json(raw_text)

    def _parse_json(self, raw_text: str) -> dict:
        """Parse JSON response, handling common issues."""
        # Try to extract JSON from markdown code blocks if present
        text = raw_text.strip()
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
                f"Qwen returned invalid JSON. Response snippet: {snippet}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError("Qwen returned JSON that is not an object")

        return data


# Convenience function for direct use
def generate_coreil_from_text(source_text: str) -> dict:
    """Generate Core IL from source text using Qwen.

    This is a convenience function that creates a QwenFrontend instance
    and calls its generate_coreil_from_text method.
    """
    frontend = QwenFrontend()
    return frontend.generate_coreil_from_text(source_text)
