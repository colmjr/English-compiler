# Migration Guide

This guide helps you migrate Core IL programs between versions.

---

## TL;DR

**All Core IL versions are backward compatible.**

To upgrade any program to v1.5:
1. Change `"version": "coreil-X.X"` to `"version": "coreil-1.5"`
2. Done!

No code changes required. All older programs are valid in newer versions.

---

## Version Compatibility Matrix

| From Version | To Version | Migration Effort |
|--------------|------------|------------------|
| v0.1-v0.5 | v1.0 | Change version string only |
| v1.0 | v1.1-v1.5 | Change version string only |
| Any version | v1.5 | Change version string only |

---

## Migration: v1.0 to v1.5

### What's New in v1.1-v1.5

**v1.5 (Current)**:
- `Slice`: Extract sublists with `arr[start:end]` semantics
- `Not`: Unary logical negation
- Negative indexing: `arr[-1]` returns last element

**v1.4**:
- `ExternalCall`: Platform-specific operations (Tier 2, Python backend only)
- Expanded string operations: `StringSplit`, `StringTrim`, `StringUpper`, `StringLower`, `StringReplace`, `StringContains`, `StringStartsWith`, `StringEndsWith`
- JavaScript backend (full parity)
- C++ backend (full parity)
- New frontends: OpenAI, Gemini, Qwen

**v1.3**:
- JSON operations: `JsonParse`, `JsonStringify`
- Regex operations: `RegexMatch`, `RegexFindAll`, `RegexReplace`, `RegexSplit`

**v1.2**:
- Math operations: `Math`, `MathPow`, `MathConst`

**v1.1**:
- `Record`: Mutable named fields
- `Set`: Set data structure with `SetHas`, `SetAdd`, `SetRemove`, `SetSize`
- `Deque`: Double-ended queue with `DequeNew`, `DequeSize`, `PushBack`, `PushFront`, `PopFront`, `PopBack`
- `Heap`: Min-heap with `HeapNew`, `HeapSize`, `HeapPeek`, `HeapPush`, `HeapPop`
- String operations: `StringLength`, `Substring`, `CharAt`, `Join`

### Migration Steps

**Step 1: Update Version String**

```json
// Before
{"version": "coreil-1.0", ...}

// After
{"version": "coreil-1.5", ...}
```

**Step 2: (Optional) Use New Features**

You can now use any v1.1-v1.5 features in your programs:

```json
// Use negative indexing (v1.5)
{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": -1}}

// Use slicing (v1.5)
{"type": "Slice", "base": {"type": "Var", "name": "arr"}, "start": {"type": "Literal", "value": 0}, "end": {"type": "Literal", "value": 3}}

// Use sets (v1.1)
{"type": "Set", "items": [{"type": "Literal", "value": 1}, {"type": "Literal", "value": 2}]}

// Use math (v1.2)
{"type": "Math", "op": "sqrt", "value": {"type": "Literal", "value": 16}}
```

### Backend Compatibility

| Feature | Interpreter | Python | JavaScript | C++ |
|---------|-------------|--------|------------|-----|
| v1.0 Core | Yes | Yes | Yes | Yes |
| v1.1 Record/Set/Deque/Heap | Yes | Yes | Yes | Yes |
| v1.2 Math | Yes | Yes | Yes | Yes |
| v1.3 JSON/Regex | Yes | Yes | Yes | Yes |
| v1.4 String ops | Yes | Yes | Yes | Yes |
| v1.4 ExternalCall | No | Yes | No | No |
| v1.5 Slice/Not/NegIdx | Yes | Yes | Yes | Yes |

Note: ExternalCall is Tier 2 (non-portable) and only works with Python backend.

---

## Migration: v0.5 to v1.0

Core IL v1.0 is 100% backward compatible with v0.5.

### What Changed in v1.0

1. **Formalized Specification**: Complete documentation in [coreil_v1.md](coreil_v1.md)
2. **Short-Circuit Evaluation**: Bug fix - `and`/`or` now properly short-circuit
3. **Tuple Indexing**: Bug fix - tuples can now be indexed
4. **Dictionary Key Order**: Bug fix - keys maintain insertion order

### Migration Steps

1. Change `"version": "coreil-0.5"` to `"version": "coreil-1.0"`
2. Test your program

---

## Migration: v0.1-v0.4 to v1.0

All v0.1-v0.4 programs work in v1.0 without modification.

### Migration Steps

1. Change version string to `"coreil-1.0"`
2. Test your program
3. Consider using v1.0 features (sealed primitives like `GetDefault`, `Keys`, `Push`)

---

## Common Migration Scenarios

### Scenario: Adding String Processing

**Before (v1.0 workaround)**:
```json
// Had to implement string operations manually or use external calls
```

**After (v1.1+)**:
```json
{"type": "StringLength", "base": {"type": "Var", "name": "str"}}
{"type": "Substring", "base": {"type": "Var", "name": "str"}, "start": {"type": "Literal", "value": 0}, "end": {"type": "Literal", "value": 5}}
```

### Scenario: Using Sets for Deduplication

**Before (v1.0)**:
```json
// Had to use dictionary with dummy values
{"type": "Let", "name": "seen", "value": {"type": "Map", "items": []}},
{"type": "Set", "base": {"type": "Var", "name": "seen"}, "key": {"type": "Var", "name": "item"}, "value": {"type": "Literal", "value": true}}
```

**After (v1.1+)**:
```json
{"type": "Let", "name": "seen", "value": {"type": "Set", "items": []}},
{"type": "SetAdd", "base": {"type": "Var", "name": "seen"}, "item": {"type": "Var", "name": "item"}}
```

### Scenario: Getting Last Element

**Before (v1.0)**:
```json
{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {
  "type": "Binary", "op": "-",
  "left": {"type": "Length", "base": {"type": "Var", "name": "arr"}},
  "right": {"type": "Literal", "value": 1}
}}
```

**After (v1.5)**:
```json
{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": -1}}
```

---

## Backward Compatibility Policy

- **Never Removed**: Old versions continue to work forever
- **Additive Only**: New versions only add features
- **Semantic Stability**: v1.0 semantics are frozen

```python
from english_compiler.coreil import SUPPORTED_VERSIONS

# All these versions work
assert "coreil-0.1" in SUPPORTED_VERSIONS
assert "coreil-0.5" in SUPPORTED_VERSIONS
assert "coreil-1.0" in SUPPORTED_VERSIONS
assert "coreil-1.5" in SUPPORTED_VERSIONS
```

---

## Testing After Migration

```bash
# Validate and run with interpreter
python -m english_compiler run your_program.coreil.json

# Compile to Python and test
python -m english_compiler compile --target python your_program.coreil.json
python your_program.py

# Compile to JavaScript and test
python -m english_compiler compile --target javascript your_program.coreil.json
node your_program.js

# Run full test suite
python -m tests.run
python -m tests.run_algorithms
```

---

## Need Help?

1. Check [CHANGELOG.md](CHANGELOG.md) for version-specific changes
2. Read [coreil_v1.md](coreil_v1.md) for complete specification
3. Look at [examples/](examples/) for working programs
4. Run tests: `python -m tests.run`

---

**Migration is always safe - full backward compatibility guaranteed.**
