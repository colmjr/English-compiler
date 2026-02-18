"""Core IL AST node navigation helpers.

This module centralizes traversal over Core IL node trees so callers do not
need to re-implement recursive dict/list walking.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, TypeGuard


def is_coreil_node(value: Any) -> TypeGuard[dict[str, Any]]:
    """Return True when value looks like a Core IL node object."""
    return isinstance(value, dict) and isinstance(value.get("type"), str)


def iter_nodes(value: Any, *, include_root: bool = True) -> Iterator[dict[str, Any]]:
    """Yield Core IL nodes from any nested dict/list structure.

    Args:
        value: A Core IL node, list, dict wrapper, or scalar.
        include_root: If True and value is a node, yield it before descendants.
    """
    if is_coreil_node(value):
        if include_root:
            yield value
        for child in value.values():
            yield from iter_nodes(child, include_root=True)
        return

    if isinstance(value, dict):
        for child in value.values():
            yield from iter_nodes(child, include_root=True)
        return

    if isinstance(value, list):
        for item in value:
            yield from iter_nodes(item, include_root=True)

