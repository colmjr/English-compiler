"""Mock LLM frontend for Core IL generation.

This mock frontend generates Core IL v1.1 programs for testing.
It provides a deterministic alternative to the Claude frontend.
"""

from __future__ import annotations


def generate_coreil_from_text(source_text: str) -> dict:
    """Generate a mock Core IL v1.1 program from source text.

    This is a simple mock that recognizes a few keywords and generates
    basic Core IL programs. Used for testing without requiring an LLM.
    """
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

    # Generate Core IL v1.1 (Print statement, not Call to "print")
    return {
        "version": "coreil-1.1",
        "ambiguities": ambiguities,
        "body": [
            {
                "type": "Print",
                "args": [
                    {"type": "Literal", "value": message}
                ],
            }
        ],
    }
