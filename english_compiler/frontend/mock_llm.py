"""Mock LLM frontend for Core IL generation."""

from __future__ import annotations


def generate_coreil_from_text(source_text: str) -> dict:
    text = source_text.lower()
    if "hello" in text:
        message = "hello"
    else:
        message = "unimplemented"

    ambiguities = []
    if "sort" in text:
        ambiguities = [
            {
                "question": "Which sort order should be used?",
                "options": ["stable", "unstable"],
                "default": 0,
            }
        ]

    return {
        "version": "coreil-0.1",
        "ambiguities": ambiguities,
        "body": [
            {
                "type": "Call",
                "name": "print",
                "args": [
                    {"type": "Literal", "value": message}
                ],
            }
        ],
    }
