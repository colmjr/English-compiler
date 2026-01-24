"""Core IL package.

Core IL v1.2 - Math Operations
==============================

This package implements the Core IL (Core Intermediate Language) v1.2 specification.

Core IL v1.2 adds:
- Math: Unary math functions (sin, cos, tan, sqrt, floor, ceil, abs, log, exp)
- MathPow: Power function (base^exponent)
- MathConst: Math constants (pi, e)

Core IL features:
- Complete: All necessary primitives for algorithmic computation
- Deterministic: Same input always produces same output
- Tested: 100% parity between interpreter and Python codegen
- Closed specification: No extension mechanism or helper functions

Version History:
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField for structured data
- v1.0: Stable release with short-circuit evaluation, tuple support (frozen)
- v0.5: Sealed primitives (GetDefault, Keys, Push, Tuple)
- v0.3: Functions and control flow (FuncDef, Return, For, ForEach)
- v0.2: Arrays and indexing
- v0.1: Basic statements and expressions

Backward Compatibility:
All v0.1-v1.1 programs continue to work in v1.2.
"""

from .interp import run_coreil
from .validate import validate_coreil

# Current version
COREIL_VERSION = "coreil-1.2"

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
])

__version__ = "1.2.0"
__all__ = ["run_coreil", "validate_coreil", "COREIL_VERSION", "SUPPORTED_VERSIONS"]
