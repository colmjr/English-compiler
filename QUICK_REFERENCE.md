# Core IL v1.0 Quick Reference

Fast reference for Core IL node types and common patterns.

---

## Document Structure

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [<statement>, ...]
}
```

---

## Expressions

### Literals and Variables

```json
{"type": "Literal", "value": 42}
{"type": "Literal", "value": "hello"}
{"type": "Literal", "value": true}
{"type": "Literal", "value": null}

{"type": "Var", "name": "x"}
```

### Binary Operations

```json
// Arithmetic: +, -, *, /, %
{"type": "Binary", "op": "+", "left": <expr>, "right": <expr>}

// Comparison: ==, !=, <, <=, >, >=
{"type": "Binary", "op": "<", "left": <expr>, "right": <expr>}

// Logical: and, or (short-circuit!)
{"type": "Binary", "op": "and", "left": <expr>, "right": <expr>}
```

### Collections

```json
// Array
{"type": "Array", "items": [<expr>, <expr>, ...]}

// Tuple (immutable)
{"type": "Tuple", "items": [<expr>, <expr>, ...]}

// Map/Dictionary
{"type": "Map", "items": []}
```

### Collection Operations

```json
// Index: arr[i]
{"type": "Index", "base": <array_or_tuple>, "index": <int_expr>}

// Length: len(arr)
{"type": "Length", "base": <array_or_tuple>}

// Get: dict[key]
{"type": "Get", "base": <map>, "key": <expr>}

// GetDefault: dict.get(key, default)
{"type": "GetDefault", "base": <map>, "key": <expr>, "default": <expr>}

// Keys: dict.keys()
{"type": "Keys", "base": <map>}
```

### Function Calls

```json
{"type": "Call", "name": "function_name", "args": [<expr>, ...]}
```

### Range (for loops only)

```json
{
  "type": "Range",
  "from": <int_expr>,
  "to": <int_expr>,
  "inclusive": false  // or true
}
```

---

## Statements

### Variables

```json
// Declare: let x = 10
{"type": "Let", "name": "x", "value": <expr>}

// Update: x = 20
{"type": "Assign", "name": "x", "value": <expr>}
```

### Collection Mutation

```json
// Array: arr[i] = value
{"type": "SetIndex", "base": <array>, "index": <expr>, "value": <expr>}

// Dictionary: dict[key] = value
{"type": "Set", "base": <map>, "key": <expr>, "value": <expr>}

// Array: arr.append(value)
{"type": "Push", "base": <array>, "value": <expr>}
```

### Control Flow

```json
// If
{
  "type": "If",
  "test": <expr>,
  "then": [<statement>, ...],
  "else": [<statement>, ...]  // optional
}

// While
{
  "type": "While",
  "test": <expr>,
  "body": [<statement>, ...]
}

// For (range)
{
  "type": "For",
  "var": "i",
  "iter": {"type": "Range", "from": 0, "to": 10, "inclusive": false},
  "body": [<statement>, ...]
}

// ForEach (collection)
{
  "type": "ForEach",
  "var": "item",
  "iter": <array_or_keys_expr>,
  "body": [<statement>, ...]
}
```

### Functions

```json
// Define
{
  "type": "FuncDef",
  "name": "add",
  "params": ["a", "b"],
  "body": [
    {"type": "Return", "value": {"type": "Binary", "op": "+", "left": {"type": "Var", "name": "a"}, "right": {"type": "Var", "name": "b"}}}
  ]
}

// Return
{"type": "Return", "value": <expr>}
```

### Output

```json
{"type": "Print", "args": [<expr>, <expr>, ...]}
```

---

## Common Patterns

### Array Sum

```json
{
  "type": "Let", "name": "sum", "value": {"type": "Literal", "value": 0}
},
{
  "type": "ForEach",
  "var": "x",
  "iter": {"type": "Var", "name": "arr"},
  "body": [
    {
      "type": "Assign",
      "name": "sum",
      "value": {
        "type": "Binary",
        "op": "+",
        "left": {"type": "Var", "name": "sum"},
        "right": {"type": "Var", "name": "x"}
      }
    }
  ]
}
```

### Dictionary Counting

```json
{
  "type": "Let", "name": "counts", "value": {"type": "Map", "items": []}
},
{
  "type": "Set",
  "base": {"type": "Var", "name": "counts"},
  "key": {"type": "Var", "name": "word"},
  "value": {
    "type": "Binary",
    "op": "+",
    "left": {
      "type": "GetDefault",
      "base": {"type": "Var", "name": "counts"},
      "key": {"type": "Var", "name": "word"},
      "default": {"type": "Literal", "value": 0}
    },
    "right": {"type": "Literal", "value": 1}
  }
}
```

### Iterate Dictionary Keys

```json
{
  "type": "ForEach",
  "var": "key",
  "iter": {"type": "Keys", "base": {"type": "Var", "name": "counts"}},
  "body": [
    {"type": "Print", "args": [{"type": "Var", "name": "key"}]}
  ]
}
```

### Safe Array Access (Guard Pattern)

```json
{
  "type": "If",
  "test": {
    "type": "Binary",
    "op": "and",
    "left": {
      "type": "Binary",
      "op": "<",
      "left": {"type": "Var", "name": "i"},
      "right": {"type": "Length", "base": {"type": "Var", "name": "arr"}}
    },
    "right": {
      "type": "Binary",
      "op": "==",
      "left": {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Var", "name": "i"}},
      "right": {"type": "Literal", "value": 0}
    }
  },
  "then": [
    {"type": "Print", "args": [{"type": "Literal", "value": "found zero"}]}
  ]
}
```

Note: This works because `and` short-circuits - `arr[i]` is only accessed if `i < len(arr)`.

### Array Swap

```json
{
  "type": "Let",
  "name": "temp",
  "value": {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Var", "name": "i"}}
},
{
  "type": "SetIndex",
  "base": {"type": "Var", "name": "arr"},
  "index": {"type": "Var", "name": "i"},
  "value": {"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Var", "name": "j"}}
},
{
  "type": "SetIndex",
  "base": {"type": "Var", "name": "arr"},
  "index": {"type": "Var", "name": "j"},
  "value": {"type": "Var", "name": "temp"}
}
```

### Tuple as Dictionary Key

```json
{
  "type": "Let",
  "name": "pair",
  "value": {
    "type": "Tuple",
    "items": [
      {"type": "Literal", "value": 1},
      {"type": "Literal", "value": 2}
    ]
  }
},
{
  "type": "Set",
  "base": {"type": "Var", "name": "counts"},
  "key": {"type": "Var", "name": "pair"},
  "value": {"type": "Literal", "value": 100}
}
```

### Fibonacci (Recursion)

```json
{
  "type": "FuncDef",
  "name": "fib",
  "params": ["n"],
  "body": [
    {
      "type": "If",
      "test": {
        "type": "Binary",
        "op": "<=",
        "left": {"type": "Var", "name": "n"},
        "right": {"type": "Literal", "value": 1}
      },
      "then": [
        {"type": "Return", "value": {"type": "Var", "name": "n"}}
      ]
    },
    {
      "type": "Return",
      "value": {
        "type": "Binary",
        "op": "+",
        "left": {
          "type": "Call",
          "name": "fib",
          "args": [
            {"type": "Binary", "op": "-", "left": {"type": "Var", "name": "n"}, "right": {"type": "Literal", "value": 1}}
          ]
        },
        "right": {
          "type": "Call",
          "name": "fib",
          "args": [
            {"type": "Binary", "op": "-", "left": {"type": "Var", "name": "n"}, "right": {"type": "Literal", "value": 2}}
          ]
        }
      }
    }
  ]
}
```

---

## Key Semantics

### Short-Circuit Evaluation

```json
// and: right is not evaluated if left is false
{"type": "Binary", "op": "and", "left": <expr>, "right": <expr>}

// or: right is not evaluated if left is true
{"type": "Binary", "op": "or", "left": <expr>, "right": <expr>}
```

Critical for guard patterns!

### Mutability

- **Mutable**: Arrays (list), Dictionaries (dict)
- **Immutable**: Tuples, Literals

### Dictionary Keys

- Keys maintain **insertion order** (Python 3.7+)
- Keys are **not sorted**
- Supports **mixed-type keys** (e.g., tuples with integers and strings)

### Scoping

- **Global**: Variables declared at top level or inside functions (functions are global)
- **Local**: Function parameters and variables declared with Let inside functions
- **Loop**: Loop variables are scoped to the loop body

### Type Checking

All type checks happen at **runtime**:
- Index requires array/tuple and non-negative integer
- Binary operators require compatible types
- Dictionary operations require dictionaries

---

## CLI Commands

```bash
# Run Core IL interpreter
python -m english_compiler run program.coreil.json

# Compile to Python
python -m english_compiler compile --target python --frontend mock program.txt

# Generate with Claude (requires ANTHROPIC_API_KEY)
python -m english_compiler compile --frontend claude program.txt

# Force regeneration
python -m english_compiler compile --regen program.txt

# Run tests
python -m tests.run
python -m tests.test_short_circuit
```

---

## Resources

- **[coreil_v1.md](coreil_v1.md)** - Complete specification
- **[examples/](examples/)** - Working programs
- **[STATUS.md](STATUS.md)** - Project status
- **[MIGRATION.md](MIGRATION.md)** - v0.5 → v1.0 upgrade guide

---

**Core IL v1.0 - Stable and Production Ready**
