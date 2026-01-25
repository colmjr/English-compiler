"""OpenAI frontend for Core IL generation."""

from __future__ import annotations

import json
import os

from english_compiler.frontend.base import BaseFrontend


class OpenAIFrontend(BaseFrontend):
    """OpenAI API frontend using the OpenAI SDK."""

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK not installed. Run: pip install openai"
            ) from exc

        self.client = openai.OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "4096"))

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
        if not raw_text:
            raise ValueError("OpenAI returned an empty response")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            snippet = raw_text[:400]
            raise ValueError(
                f"OpenAI returned invalid JSON. Response snippet: {snippet}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError("OpenAI returned JSON that is not an object")

        return data


# Convenience function for direct use
def generate_coreil_from_text(source_text: str) -> dict:
    """Generate Core IL from source text using OpenAI.

    This is a convenience function that creates an OpenAIFrontend instance
    and calls its generate_coreil_from_text method.
    """
    frontend = OpenAIFrontend()
    return frontend.generate_coreil_from_text(source_text)
