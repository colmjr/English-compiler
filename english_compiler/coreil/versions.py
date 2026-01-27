"""Core IL version constants.

This module is the single source of truth for all Core IL version information.
All other modules should import version constants from here.

Version History:
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2)
- v1.5: Added Slice, negative indexing, unary Not
- v1.4: Consolidated v1.2 Math + v1.3 JSON/Regex operations
- v1.3: Added JSON operations (JsonParse, JsonStringify) and Regex operations
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField, Set, Deque, String operations
- v1.0: Stable release with short-circuit evaluation, tuple support (frozen)
- v0.5: Sealed primitives (GetDefault, Keys, Push, Tuple)
- v0.3: Functions and control flow (FuncDef, Return, For, ForEach)
- v0.2: Arrays and indexing
- v0.1: Basic statements and expressions
"""

from __future__ import annotations

# Current stable version
COREIL_VERSION = "coreil-1.6"

# All supported versions (for backward compatibility)
SUPPORTED_VERSIONS = frozenset([
    "coreil-0.1",
    "coreil-0.2",
    "coreil-0.3",
    "coreil-0.4",
    "coreil-0.5",
    "coreil-1.0",
    "coreil-1.1",
    "coreil-1.2",
    "coreil-1.3",
    "coreil-1.4",
    "coreil-1.5",
    "coreil-1.6",
])

# Package version (semantic versioning)
PACKAGE_VERSION = "1.7.2"


def is_version_supported(version: str) -> bool:
    """Check if a Core IL version string is supported."""
    return version in SUPPORTED_VERSIONS


def is_sealed_version(version: str) -> bool:
    """Check if a version uses sealed primitives (v0.5+).

    In sealed versions, helper functions like get_or_default, keys, append
    are disallowed - programs must use explicit primitives.
    """
    if not version or not version.startswith("coreil-"):
        return False
    try:
        parts = version.replace("coreil-", "").split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        # v0.5+ and v1.x+ are sealed
        return (major == 0 and minor >= 5) or major >= 1
    except (ValueError, IndexError):
        return False


def get_version_error_message() -> str:
    """Get a formatted error message listing all supported versions."""
    sorted_versions = sorted(
        SUPPORTED_VERSIONS,
        key=lambda v: [int(x) for x in v.replace("coreil-", "").split(".")]
    )
    return f"version must be one of: {', '.join(repr(v) for v in sorted_versions)}"
