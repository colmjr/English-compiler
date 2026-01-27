"""Qwen frontend for Core IL generation."""

from __future__ import annotations

import os

from english_compiler.frontend.base import BaseFrontend, get_env_int, get_required_env


class QwenFrontend(BaseFrontend):
    """Qwen API frontend using DashScope or OpenAI-compatible endpoint.

    Supports two modes:
    1. DashScope SDK (default): Uses Alibaba Cloud's dashscope library
    2. OpenAI-compatible: Set QWEN_BASE_URL to use OpenAI SDK with Qwen endpoint
    """

    def __init__(self) -> None:
        super().__init__()
        api_key = get_required_env("QWEN_API_KEY")

        self.model = os.getenv("QWEN_MODEL", "qwen-turbo")
        self.max_tokens = get_env_int("QWEN_MAX_TOKENS", 4096, min_value=1)
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
        # DashScope may return markdown-wrapped JSON, so strip it
        return self._parse_json_response(raw_text, "Qwen", strip_markdown=True)

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
        return self._parse_json_response(raw_text, "Qwen")
