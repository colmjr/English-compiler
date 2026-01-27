"""Gemini frontend for Core IL generation."""

from __future__ import annotations

import os

from english_compiler.frontend.base import BaseFrontend, get_required_env


class GeminiFrontend(BaseFrontend):
    """Google Gemini API frontend using the google-generativeai SDK."""

    def __init__(self) -> None:
        super().__init__()
        api_key = get_required_env("GEMINI_API_KEY")

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
        return self._parse_json_response(raw_text, "Gemini")
