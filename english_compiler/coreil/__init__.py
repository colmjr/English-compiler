"""Core IL package.

Core IL v1.0 - Stable and Production Ready
==========================================

This package implements the Core IL (Core Intermediate Language) v1.0 specification.

Core IL v1.0 is:
- Stable: Specification is frozen, no breaking changes
- Complete: All necessary primitives for algorithmic computation
- Deterministic: Same input always produces same output
- Tested: 100% parity between interpreter and Python codegen

Version History:
- v1.0: Stable release with short-circuit evaluation, tuple support, frozen spec
- v0.5: Sealed primitives (GetDefault, Keys, Push, Tuple)
- v0.3: Functions and control flow (FuncDef, Return, For, ForEach)
- v0.2: Arrays and indexing
- v0.1: Basic statements and expressions

Backward Compatibility:
All v0.1-v0.5 programs continue to work in v1.0.
"""

from .interp import run_coreil
from .validate import validate_coreil

# Current stable version
COREIL_VERSION = "coreil-1.0"

# All supported versions (for backward compatibility)
SUPPORTED_VERSIONS = frozenset([
    "coreil-0.1",
    "coreil-0.2",
    "coreil-0.3",
    "coreil-0.4",
    "coreil-0.5",
    "coreil-1.0",
])

__version__ = "1.0.0"
__all__ = ["run_coreil", "validate_coreil", "COREIL_VERSION", "SUPPORTED_VERSIONS"]
