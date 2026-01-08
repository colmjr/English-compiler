"""Mock LLM frontend for Core IL generation."""

from __future__ import annotations


def generate_coreil_from_text(source_text: str) -> dict:
    text = source_text.lower()
    if "hello" in text:
        message = "hello"
    else:
        message = "unimplemented"

    return {
        "version": "coreil-0.1",
        "ambiguities": [],
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
