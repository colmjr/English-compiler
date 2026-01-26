"""Core IL package.

Core IL v1.5 - Array Slicing and Unary Not
==========================================

This package implements the Core IL (Core Intermediate Language) v1.5 specification.

Core IL v1.5 adds:
- Slice: Array/list slicing operations
- Not: Logical negation

Core IL features:
- Complete: All necessary primitives for algorithmic computation
- Deterministic: Same input always produces same output
- Tested: 100% parity between interpreter and Python codegen
- Closed specification: No extension mechanism or helper functions

Version History:
- v1.5: Added Slice for array/list slicing, Not for logical negation
- v1.4: Consolidated v1.2 Math + v1.3 JSON/Regex operations
- v1.3: Added JSON operations (JsonParse, JsonStringify) and Regex operations
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField for structured data
- v1.0: Stable release with short-circuit evaluation, tuple support (frozen)
- v0.5: Sealed primitives (GetDefault, Keys, Push, Tuple)
- v0.3: Functions and control flow (FuncDef, Return, For, ForEach)
- v0.2: Arrays and indexing
- v0.1: Basic statements and expressions

Backward Compatibility:
All v0.1-v1.4 programs continue to work in v1.5.
"""

from .interp import run_coreil
from .validate import validate_coreil
from .emit import emit_python
from .emit_javascript import emit_javascript
from .versions import COREIL_VERSION, SUPPORTED_VERSIONS, PACKAGE_VERSION

__version__ = PACKAGE_VERSION
__all__ = [
    "run_coreil",
    "validate_coreil",
    "emit_python",
    "emit_javascript",
    "COREIL_VERSION",
    "SUPPORTED_VERSIONS",
]
