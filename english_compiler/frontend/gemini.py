"""Gemini frontend for Core IL generation."""

from __future__ import annotations

import json
import os

from english_compiler.frontend.base import BaseFrontend


class GeminiFrontend(BaseFrontend):
    """Google Gemini API frontend using the google-generativeai SDK."""

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "Google Generative AI SDK not installed. "
                "Run: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )

    def get_model_name(self) -> str:
        return self.model_name

    def _call_api(self, user_message: str) -> dict:
        """Call Gemini API with JSON response format."""
        response = self.model.generate_content(user_message)

        raw_text = response.text
        if not raw_text:
            raise ValueError("Gemini returned an empty response")

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            snippet = raw_text[:400]
            raise ValueError(
                f"Gemini returned invalid JSON. Response snippet: {snippet}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError("Gemini returned JSON that is not an object")

        return data


# Convenience function for direct use
def generate_coreil_from_text(source_text: str) -> dict:
    """Generate Core IL from source text using Gemini.

    This is a convenience function that creates a GeminiFrontend instance
    and calls its generate_coreil_from_text method.
    """
    frontend = GeminiFrontend()
    return frontend.generate_coreil_from_text(source_text)
