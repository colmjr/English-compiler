"""Core IL package.

Core IL v1.6 - OOP-Style Method Calls and Property Access
=========================================================

This package implements the Core IL (Core Intermediate Language) v1.6 specification.

Core IL v1.6 adds:
- MethodCall: Call a method on an object (obj.method(args))
- PropertyGet: Access a property on an object (obj.property)
These are Tier 2 (non-portable) operations for OOP-style library APIs.

Core IL features:
- Complete: All necessary primitives for algorithmic computation
- Deterministic: Same input always produces same output
- Tested: 100% parity between interpreter and Python codegen
- Closed specification: No extension mechanism or helper functions

Version History:
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2)
- v1.5: Added Slice expression for list slicing
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
All v0.1-v1.5 programs continue to work in v1.6.
"""

from .interp import run_coreil
from .validate import validate_coreil
from .emit import emit_python
from .emit_javascript import emit_javascript

# Current version
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

__version__ = "1.6.0"
__all__ = [
    "run_coreil",
    "validate_coreil",
    "emit_python",
    "emit_javascript",
    "COREIL_VERSION",
    "SUPPORTED_VERSIONS",
]
