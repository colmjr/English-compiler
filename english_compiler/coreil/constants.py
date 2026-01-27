"""Shared constants for Core IL.

This module centralizes constants used across validate.py, interp.py, and other
Core IL modules to ensure consistency and reduce duplication.
"""

from __future__ import annotations


# Binary operators supported in Core IL
BINARY_OPS = frozenset({
    "+",
    "-",
    "*",
    "/",
    "%",
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "and",
    "or",
})

# Math operations supported in Core IL v1.2+
MATH_OPS = frozenset({
    "sin",
    "cos",
    "tan",
    "sqrt",
    "floor",
    "ceil",
    "abs",
    "log",
    "exp",
})

# Math constants supported in Core IL v1.2+
MATH_CONSTANTS = frozenset({"pi", "e"})

# Maximum call depth for recursion
MAX_CALL_DEPTH = 1000

# Helper functions disallowed in sealed versions (v0.5+)
# Must use explicit primitives instead
DISALLOWED_HELPER_CALLS = frozenset({
    "get_or_default",
    "keys",
    "append",
    "entries",
})
