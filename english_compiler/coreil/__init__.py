"""Core IL package.

Core IL v1.9 - Type Conversion Expressions
===========================================

This package implements the Core IL (Core Intermediate Language) v1.9 specification.

Core IL v1.9 adds:
- ToInt, ToFloat, ToString type conversion expressions

Core IL features:
- Complete: All necessary primitives for algorithmic computation
- Deterministic: Same input always produces same output
- Tested: 100% parity between interpreter and Python codegen
- Closed specification: No extension mechanism or helper functions

Version History:
- v1.9: Added ToInt, ToFloat, ToString type conversion expressions
- v1.8: Added Throw and TryCatch for exception handling
- v1.7: Added Break and Continue loop control statements
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2)
- v1.5: Added Slice, negative indexing, unary Not
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
All v0.1-v1.8 programs continue to work in v1.9.
"""

from .interp import run_coreil
from .validate import validate_coreil
from .emit import emit_python
from .emit_javascript import emit_javascript
from .debug import debug_coreil
from .versions import COREIL_VERSION, SUPPORTED_VERSIONS, PACKAGE_VERSION

__version__ = PACKAGE_VERSION
__all__ = [
    "run_coreil",
    "validate_coreil",
    "emit_python",
    "emit_javascript",
    "debug_coreil",
    "COREIL_VERSION",
    "SUPPORTED_VERSIONS",
]
