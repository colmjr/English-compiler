"""Source map composition for English → Core IL → target language.

Composes two-stage source maps:
1. English line → Core IL statement indices (from LLM frontend)
2. Core IL statement index → target language line numbers (from emitter)

The composition gives: English line → target language line numbers.
"""

from __future__ import annotations


def compose_source_maps(
    english_to_coreil: dict[str, list[int]],
    coreil_to_target: dict[int, list[int]],
) -> dict[str, list[int]]:
    """Compose English→CoreIL and CoreIL→target into English→target.

    Args:
        english_to_coreil: Maps English line numbers (string keys, 1-indexed)
            to lists of Core IL body statement indices (0-indexed).
        coreil_to_target: Maps Core IL body statement indices (0-indexed)
            to lists of target language line numbers (0-indexed).

    Returns:
        Dict mapping English line numbers to sorted target language line numbers.
    """
    result: dict[str, list[int]] = {}
    for eng_line, coreil_indices in english_to_coreil.items():
        target_lines: list[int] = []
        for ci in coreil_indices:
            target_lines.extend(coreil_to_target.get(ci, []))
        if target_lines:
            result[eng_line] = sorted(target_lines)
    return result
