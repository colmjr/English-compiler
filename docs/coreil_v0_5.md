# Core IL v0.5: Sealed Primitives

**Version:** coreil-0.5
**Date:** 2026-01-10

## Overview

Version 0.5 "seals" the Core IL by adding explicit primitives for common map and list operations, eliminating the need for unbounded helper function calls.

**Key changes:**
- Added explicit primitives: `GetDefault`, `Keys`, `Push`, `Tuple`
- Restricted `Call` nodes to user-defined functions only (no invented helpers)
- All operations now have deterministic semantics

## Motivation

In v0.4, `Call` nodes could reference arbitrary function names like `get_or_default`, `keys`, `append`. This created:
1. **Unbounded "stdlib" problem**: No contract on what functions exist
2. **Non-deterministic codegen**: Python generation failed for unknown functions
3. **Semantic ambiguity**: Behavior of helpers was undefined

v0.5 solves this by making all operations explicit IR nodes with well-defined semantics.

## New Primitives

### 1. GetDefault (Expression)

Get value from map with fallback default.

```json
{
  "type": "GetDefault",
  "base": <map_expr>,
  "key": <key_expr>,
  "default": <default_expr>
}
```

**Semantics:**
- Evaluates `base` to a map/dict
- Evaluates `key`
- If `key` exists in map, returns associated value
- Otherwise, returns evaluated `default`

**Python equivalent:** `base.get(key, default)`

**Example:**
```json
{
  "type": "GetDefault",
  "base": {"type": "Var", "name": "counts"},
  "key": {"type": "Tuple", "items": [
    {"type": "Literal", "value": "a"},
    {"type": "Literal", "value": "b"}
  ]},
  "default": {"type": "Literal", "value": 0}
}
```

### 2. Keys (Expression)

Extract all keys from a map as an array.

```json
{
  "type": "Keys",
  "base": <map_expr>
}
```

**Semantics:**
- Evaluates `base` to a map/dict
- Returns array of all keys in **sorted order** (for determinism)
- Keys are sorted if comparable (numbers, strings)
- Mixed-type keys preserve insertion order

**Python equivalent:** `sorted(base.keys())` (when keys are comparable)

**Example:**
```json
{
  "type": "Keys",
  "base": {"type": "Var", "name": "counts"}
}
```

**Iteration pattern:**
```json
{
  "type": "ForEach",
  "var": "key",
  "iter": {
    "type": "Keys",
    "base": {"type": "Var", "name": "counts"}
  },
  "body": [...]
}
```

### 3. Push (Statement)

Append value to end of array (mutating operation).

```json
{
  "type": "Push",
  "base": <array_expr>,
  "value": <value_expr>
}
```

**Semantics:**
- Evaluates `base` to an array/list
- Evaluates `value`
- Appends `value` to end of array (mutation)
- Returns nothing (statement only)

**Python equivalent:** `base.append(value)`

**Example:**
```json
{
  "type": "Push",
  "base": {"type": "Var", "name": "results"},
  "value": {"type": "Literal", "value": 42}
}
```

### 4. Tuple (Expression)

Create immutable tuple (hashable, suitable for map keys).

```json
{
  "type": "Tuple",
  "items": [<expr>, ...]
}
```

**Semantics:**
- Evaluates each item expression
- Returns immutable tuple of values
- Tuples are hashable (can be used as map keys)
- Tuples support equality comparison

**Python equivalent:** `(item1, item2, ...)`

**Example:**
```json
{
  "type": "Tuple",
  "items": [
    {"type": "Literal", "value": "hello"},
    {"type": "Literal", "value": "world"}
  ]
}
```

**Bigram counting pattern:**
```json
{
  "type": "Let",
  "name": "counts",
  "value": {"type": "Map", "items": []}
},
{
  "type": "Set",
  "base": {"type": "Var", "name": "counts"},
  "key": {
    "type": "Tuple",
    "items": [
      {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Var", "name": "i"}},
      {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}}}
    ]
  },
  "value": {
    "type": "Binary",
    "op": "+",
    "left": {
      "type": "GetDefault",
      "base": {"type": "Var", "name": "counts"},
      "key": {"type": "Tuple", "items": [...]},
      "default": {"type": "Literal", "value": 0}
    },
    "right": {"type": "Literal", "value": 1}
  }
}
```

## Restricted Call Semantics

### Call nodes (v0.5)

In v0.5, `Call` is **restricted** to user-defined functions only.

**Valid calls:**
- Functions defined by `FuncDef` in the same program
- Example: `{"type": "Call", "name": "my_function", "args": [...]}`

**Invalid calls (rejected by validator):**
- `get_or_default` → Use `GetDefault` instead
- `keys` → Use `Keys` instead
- `append` → Use `Push` instead
- Any other undefined function name

**Note:** If you need to support built-in functions in the future (e.g., `sqrt`, `abs`), add them to an explicit allowlist in the validator.

## Migration from v0.4

### get_or_default → GetDefault

**Before (v0.4):**
```json
{
  "type": "Call",
  "name": "get_or_default",
  "args": [
    {"type": "Var", "name": "map"},
    {"type": "Literal", "value": "key"},
    {"type": "Literal", "value": "default"}
  ]
}
```

**After (v0.5):**
```json
{
  "type": "GetDefault",
  "base": {"type": "Var", "name": "map"},
  "key": {"type": "Literal", "value": "key"},
  "default": {"type": "Literal", "value": "default"}
}
```

### keys → Keys

**Before (v0.4):**
```json
{
  "type": "Call",
  "name": "keys",
  "args": [{"type": "Var", "name": "map"}]
}
```

**After (v0.5):**
```json
{
  "type": "Keys",
  "base": {"type": "Var", "name": "map"}
}
```

### append → Push

**Before (v0.4):**
```json
{
  "type": "Call",
  "name": "append",
  "args": [
    {"type": "Var", "name": "list"},
    {"type": "Literal", "value": 42}
  ]
}
```

**After (v0.5):**
```json
{
  "type": "Push",
  "base": {"type": "Var", "name": "list"},
  "value": {"type": "Literal", "value": 42}
}
```

### Array keys → Tuple keys

**Before (v0.4):**
```json
{
  "type": "Map",
  "items": [
    {
      "key": {
        "type": "Array",
        "items": [
          {"type": "Literal", "value": "a"},
          {"type": "Literal", "value": "b"}
        ]
      },
      "value": {"type": "Literal", "value": 1}
    }
  ]
}
```

**After (v0.5):**
```json
{
  "type": "Map",
  "items": [
    {
      "key": {
        "type": "Tuple",
        "items": [
          {"type": "Literal", "value": "a"},
          {"type": "Literal", "value": "b"}
        ]
      },
      "value": {"type": "Literal", "value": 1}
    }
  ]
}
```

## Complete Example: Bigram Counting

This example demonstrates all new v0.5 primitives:

```json
{
  "version": "coreil-0.5",
  "ambiguities": [],
  "body": [
    {
      "type": "Let",
      "name": "arr",
      "value": {
        "type": "Array",
        "items": [
          {"type": "Literal", "value": "a"},
          {"type": "Literal", "value": "b"},
          {"type": "Literal", "value": "c"},
          {"type": "Literal", "value": "a"},
          {"type": "Literal", "value": "b"}
        ]
      }
    },
    {
      "type": "Let",
      "name": "counts",
      "value": {"type": "Map", "items": []}
    },
    {
      "type": "Let",
      "name": "i",
      "value": {"type": "Literal", "value": 0}
    },
    {
      "type": "While",
      "test": {
        "type": "Binary",
        "op": "<",
        "left": {"type": "Var", "name": "i"},
        "right": {
          "type": "Binary",
          "op": "-",
          "left": {"type": "Length", "base": {"type": "Var", "name": "arr"}},
          "right": {"type": "Literal", "value": 1}
        }
      },
      "body": [
        {
          "type": "Let",
          "name": "pair",
          "value": {
            "type": "Tuple",
            "items": [
              {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Var", "name": "i"}},
              {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {
                "type": "Binary", "op": "+", "left": {"type": "Var", "name": "i"}, "right": {"type": "Literal", "value": 1}
              }}
            ]
          }
        },
        {
          "type": "Set",
          "base": {"type": "Var", "name": "counts"},
          "key": {"type": "Var", "name": "pair"},
          "value": {
            "type": "Binary",
            "op": "+",
            "left": {
              "type": "GetDefault",
              "base": {"type": "Var", "name": "counts"},
              "key": {"type": "Var", "name": "pair"},
              "default": {"type": "Literal", "value": 0}
            },
            "right": {"type": "Literal", "value": 1}
          }
        },
        {
          "type": "Assign",
          "name": "i",
          "value": {
            "type": "Binary",
            "op": "+",
            "left": {"type": "Var", "name": "i"},
            "right": {"type": "Literal", "value": 1}
          }
        }
      ]
    },
    {
      "type": "Print",
      "args": [{"type": "Var", "name": "counts"}]
    }
  ]
}
```

**Expected output:**
```
{('a', 'b'): 2, ('b', 'c'): 1, ('c', 'a'): 1}
```

## Backward Compatibility

Programs marked `coreil-0.1` through `coreil-0.4` remain valid. The validator/interpreter should:
- Accept v0.1-0.4 programs with helper Call nodes (for backward compatibility)
- Recommend upgrading to v0.5 for new programs
- Show warnings when encountering helper calls in v0.5+ programs

New programs should use `"version": "coreil-0.5"` and use the explicit primitives.

## Summary

v0.5 makes Core IL **sealed** and **deterministic**:
- ✅ All operations have explicit IR nodes
- ✅ No unbounded "stdlib" via Call
- ✅ Deterministic Python codegen
- ✅ Clear semantics for all primitives
- ✅ Hashable tuple keys for maps
