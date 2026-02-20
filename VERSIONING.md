# Core IL Versioning and Code Hygiene

**Date:** 2026-01-26
**Status:** Complete

---

## Overview

This document describes the Core IL v1.5 versioning strategy and code hygiene standards implemented throughout the codebase.

---

## Version Strategy

### Current Stable Version

**Core IL v1.5** (`"coreil-1.5"`)

- Latest stable version with all features
- Production-ready with 100% test coverage
- Fully documented in [coreil_v1.md](coreil_v1.md)

### Backward Compatibility

The implementation accepts all versions from v0.1 through v1.5:

```python
SUPPORTED_VERSIONS = frozenset([
    "coreil-0.1",  # Basic statements and expressions
    "coreil-0.2",  # Arrays and indexing
    "coreil-0.3",  # Functions and control flow
    "coreil-0.4",  # (reserved/unused)
    "coreil-0.5",  # Sealed primitives
    "coreil-1.0",  # Stable release (frozen)
    "coreil-1.1",  # Record, Set, Deque, Heap, String ops
    "coreil-1.2",  # Math operations
    "coreil-1.3",  # JSON and Regex operations
    "coreil-1.4",  # ExternalCall, expanded string ops, JS/C++ backends
    "coreil-1.5",  # Slice, Not, negative indexing (current)
])
```

**Policy**: Old versions continue to work indefinitely. New programs should use v1.5.

---

## Version Markers in Code

All key implementation files include explicit version markers:

### 1. Package Level

[english_compiler/coreil/versions.py](english_compiler/coreil/versions.py)

```python
# Current stable version
COREIL_VERSION = "coreil-1.5"

# All supported versions (for backward compatibility)
SUPPORTED_VERSIONS = frozenset([
    "coreil-0.1", "coreil-0.2", "coreil-0.3",
    "coreil-0.4", "coreil-0.5", "coreil-1.0",
    "coreil-1.1", "coreil-1.2", "coreil-1.3",
    "coreil-1.4", "coreil-1.5",
])

# Package version
PACKAGE_VERSION = "1.5.0"
```

**Usage**:
```python
from english_compiler.coreil import COREIL_VERSION, SUPPORTED_VERSIONS

# Check if version is supported
if doc["version"] not in SUPPORTED_VERSIONS:
    raise ValueError(f"Unsupported version: {doc['version']}")

# Use current version for new programs
new_doc = {"version": COREIL_VERSION, "body": [...]}
```

### 2. Validator

[english_compiler/coreil/validate.py](english_compiler/coreil/validate.py)

**Module docstring**:
```python
"""Core IL validation.

This file implements Core IL v1.5 semantics validation.
Core IL v1.0 is stable and frozen - no breaking changes will be made.

Backward compatibility: Accepts v0.1 through v1.5 programs.
"""
```

### 3. Interpreter

[english_compiler/coreil/interp.py](english_compiler/coreil/interp.py)

**Module docstring**:
```python
"""Core IL interpreter.

This file implements Core IL v1.5 semantics interpreter.
Core IL v1.0 is stable and frozen - no breaking changes will be made.

Key features:
- Short-circuit evaluation for 'and' and 'or' operators
- Tuple indexing and length support
- Dictionary insertion order preservation
- Negative indexing support
- Recursion limit: 100 calls

Backward compatibility: Accepts v0.1 through v1.5 programs.
"""
```

### 4. Code Generators

[english_compiler/coreil/emit.py](english_compiler/coreil/emit.py) - Python
[english_compiler/coreil/emit_javascript.py](english_compiler/coreil/emit_javascript.py) - JavaScript
[english_compiler/coreil/emit_cpp.py](english_compiler/coreil/emit_cpp.py) - C++

All code generators include version markers and support the full v1.5 specification.

### 5. Frontends

[english_compiler/frontend/claude.py](english_compiler/frontend/claude.py)
[english_compiler/frontend/openai_provider.py](english_compiler/frontend/openai_provider.py)
[english_compiler/frontend/gemini.py](english_compiler/frontend/gemini.py)
[english_compiler/frontend/qwen.py](english_compiler/frontend/qwen.py)

All frontends generate v1.5 programs by default.

---

## Versioning Rules

### For New Code

**Always use the current version for new programs**:

```python
from english_compiler.coreil import COREIL_VERSION

doc = {
    "version": COREIL_VERSION,  # "coreil-1.5"
    "ambiguities": [],
    "body": [...]
}
```

### For Validation

**Accept all supported versions**:

```python
from english_compiler.coreil import SUPPORTED_VERSIONS

if doc["version"] not in SUPPORTED_VERSIONS:
    raise ValueError(f"Unsupported version: {doc['version']}")
```

### For Tests

**Tests should use current version for new test cases**, but continue testing backward compatibility:

```python
# New test (use current version)
def test_new_feature():
    doc = {"version": "coreil-1.5", ...}

# Backward compat test
def test_old_version_works():
    doc = {"version": "coreil-0.2", ...}  # Still works!
```

---

## Error Messages

All version-related errors include the full list of supported versions:

```
ValueError: version must be one of: 'coreil-0.1', 'coreil-0.2', 'coreil-0.3',
            'coreil-0.4', 'coreil-0.5', 'coreil-1.0', 'coreil-1.1', 'coreil-1.2',
            'coreil-1.3', 'coreil-1.4', 'coreil-1.5'
```

This makes it clear:
1. What versions are supported
2. That v1.5 is the latest
3. That backward compatibility is maintained

---

## Code Hygiene Standards

### 1. Module Docstrings

Every Core IL implementation file includes:

- **Version marker**: "This file implements Core IL v1.5 semantics"
- **Stability guarantee**: "Core IL v1.0 is stable and frozen"
- **Backward compatibility note**: "Accepts v0.1 through v1.5 programs"
- **Key features** (where applicable)

### 2. Version Comments

Version checks in code include explanatory comments:

```python
# Core IL Version Check
# v1.5 is the current stable version
# v0.1-v1.4 are accepted for backward compatibility
if doc.get("version") not in SUPPORTED_VERSIONS:
    raise ValueError(...)
```

### 3. Constants Over Magic Strings

Use named constants instead of hardcoded version strings:

```python
# Good
from english_compiler.coreil import COREIL_VERSION
doc = {"version": COREIL_VERSION, ...}

# Avoid
doc = {"version": "coreil-1.5", ...}
```

### 4. Centralized Version Management

Version constants are defined once in `english_compiler/coreil/versions.py` and imported everywhere else.

---

## Testing Version Handling

### Test Current Version

```bash
$ python -m english_compiler run examples/hello_v1.coreil.json
Hello from Core IL v1.0!
```

### Test Backward Compatibility

```bash
# v0.2 program still works
$ python -m english_compiler run examples/bubble_sort.coreil.json
[1, 2, 3, 4, 5, 6, 7]
```

### Test Version Constants

```python
from english_compiler.coreil import COREIL_VERSION, SUPPORTED_VERSIONS

assert COREIL_VERSION == "coreil-1.5"
assert "coreil-0.1" in SUPPORTED_VERSIONS
assert "coreil-1.0" in SUPPORTED_VERSIONS
assert "coreil-1.5" in SUPPORTED_VERSIONS
assert "coreil-2.0" not in SUPPORTED_VERSIONS
```

---

## Version Evolution Policy

### Adding New Versions (Future)

If Core IL v1.6 or v2.0 is created:

1. Update `COREIL_VERSION` to the new version
2. Add new version to `SUPPORTED_VERSIONS`
3. Keep all old versions in `SUPPORTED_VERSIONS`
4. Update module docstrings
5. Document changes in [CHANGELOG.md](CHANGELOG.md)

**Critical**: Never remove old versions from `SUPPORTED_VERSIONS`. Backward compatibility is permanent.

### Version Numbering

- **Major version** (v1.0 → v2.0): Breaking semantic changes
- **Minor version** (v1.0 → v1.1): New features, backward compatible
- **Patch version**: Not used in Core IL (only in package version)

**v1.0 Promise**: Core IL v1.0 semantics are frozen forever. Programs written in v1.0 will always work.

---

## Summary of Versions

| Version | Key Features | Status |
|---------|-------------|--------|
| v1.10.5 | Import (multi-file modules) | Current |
| v1.5 | Slice, Not, negative indexing | Stable |
| v1.4 | ExternalCall, JS/C++ backends, expanded strings | Stable |
| v1.3 | JSON, Regex operations | Stable |
| v1.2 | Math operations | Stable |
| v1.1 | Record, Set, Deque, Heap, strings | Stable |
| v1.0 | Short-circuit, Tuple, sealed primitives | Frozen |
| v0.5 | Sealed primitives | Legacy |
| v0.3 | Functions, loops | Legacy |
| v0.2 | Arrays | Legacy |
| v0.1 | Basic | Legacy |

---

## Backward Compatibility

**100% Maintained**

- All v0.1-v1.4 programs continue to work in v1.5
- No breaking changes introduced
- All tests pass

---

## Conclusion

Core IL v1.5 is now clearly marked throughout the codebase as:

1. **Current**: v1.5 is the latest stable version
2. **Feature-Rich**: Includes all v1.1-v1.5 enhancements
3. **Backward Compatible**: v0.1-v1.4 programs still work
4. **Well-Documented**: Every file explains version policy

The codebase now has:
- Central version constants
- Consistent version comments
- Clear stability guarantees
- Comprehensive documentation

**Core IL v1.5 versioning is complete and production-ready.**
