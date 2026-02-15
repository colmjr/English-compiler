# Core IL v1.8 Quick Reference

Fast reference for Core IL node types and common patterns.

---

## Document Structure

```json
{
  "version": "coreil-1.8",
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
{"type": "Binary", "op": "<", "left": <expr>, "right": <expr|}

// Logical: and, or (short-circuit!)
{"type": "Binary", "op": "and", "left": <expr>, "right": <expr>}
```

### Unary Not (v1.5)

```json
{"type": "Not", "value": <expr>}
```

### Collections

```json
// Array
{"type": "Array", "items": [<expr>, <expr>, ...]}

// Tuple (immutable)
{"type": "Tuple", "items": [<expr>, <expr>, ...]}

// Map/Dictionary
{"type": "Map", "items": []}

// Record (v1.1) - mutable named fields
{"type": "Record", "fields": {"x": <expr>, "y": <expr>}}

// Set (v1.1) - unique elements
{"type": "Set", "items": [<expr>, <expr>, ...]}
```

### Collection Operations

```json
// Index: arr[i] (supports negative indices in v1.5)
{"type": "Index", "base": <array_or_tuple>, "index": <int_expr>}

// Slice: arr[start:end] (v1.5)
{"type": "Slice", "base": <array>, "start": <expr>, "end": <expr>}

// Length: len(arr)
{"type": "Length", "base": <array_or_tuple>}

// Get: dict[key]
{"type": "Get", "base": <map>, "key": <expr>}

// GetDefault: dict.get(key, default)
{"type": "GetDefault", "base": <map>, "key": <expr>, "default": <expr>}

// Keys: dict.keys()
{"type": "Keys", "base": <map>}
```

### Record Operations (v1.1)

```json
// Create record
{"type": "Record", "fields": {"name": <expr>, "age": <expr>}}

// Get field
{"type": "GetField", "base": <record>, "field": "name"}
```

### Set Operations (v1.1)

```json
// Create set
{"type": "Set", "items": [<expr>, ...]}

// Check membership
{"type": "SetHas", "base": <set>, "item": <expr>}

// Get size
{"type": "SetSize", "base": <set>}
```

### Deque Operations (v1.1)

```json
// Create empty deque
{"type": "DequeNew"}

// Get size
{"type": "DequeSize", "base": <deque>}
```

### Heap Operations (v1.1)

```json
// Create empty min-heap
{"type": "HeapNew"}

// Get size
{"type": "HeapSize", "base": <heap>}

// View top element (doesn't remove)
{"type": "HeapPeek", "base": <heap>}
```

### String Operations (v1.1+)

```json
// String length (v1.1)
{"type": "StringLength", "base": <string>}

// Substring (v1.1)
{"type": "Substring", "base": <string>, "start": <expr>, "end": <expr|}

// Character at index (v1.1)
{"type": "CharAt", "base": <string>, "index": <expr>}

// Join array to string (v1.1)
{"type": "Join", "items": <array>, "separator": <string>}

// Split string (v1.4)
{"type": "StringSplit", "base": <string>, "separator": <string>}

// Trim whitespace (v1.4)
{"type": "StringTrim", "base": <string>}

// Convert case (v1.4)
{"type": "StringUpper", "base": <string>}
{"type": "StringLower", "base": <string>}

// Replace substring (v1.4)
{"type": "StringReplace", "base": <string>, "old": <string>, "new": <string>}

// Check contains (v1.4)
{"type": "StringContains", "base": <string>, "substring": <string>}

// Check prefix/suffix (v1.4)
{"type": "StringStartsWith", "base": <string>, "prefix": <string>}
{"type": "StringEndsWith", "base": <string>, "suffix": <string>}
```

### Math Operations (v1.2)

```json
// Unary math: sin, cos, tan, sqrt, floor, ceil, abs, log, exp
{"type": "Math", "op": "sqrt", "value": <expr>}

// Power
{"type": "MathPow", "base": <expr>, "exponent": <expr>}

// Constants: pi, e
{"type": "MathConst", "name": "pi"}
```

### JSON Operations (v1.3)

```json
// Parse JSON string
{"type": "JsonParse", "value": <string_expr>}

// Convert to JSON string
{"type": "JsonStringify", "value": <expr>}
```

### Regex Operations (v1.3)

```json
// Test if matches
{"type": "RegexMatch", "pattern": <string>, "text": <string>}

// Find all matches
{"type": "RegexFindAll", "pattern": <string>, "text": <string>}
```

### Function Calls

```json
{"type": "Call", "name": "function_name", "args": [<expr>, ...]}
```

### External Calls (v1.4, Tier 2)

```json
{"type": "ExternalCall", "module": "time", "function": "time", "args": []}
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

// Record field: record.field = value (v1.1)
{"type": "SetField", "base": <record>, "field": "name", "value": <expr>}

// Set: add item (v1.1)
{"type": "SetAdd", "base": <set>, "item": <expr>}

// Set: remove item (v1.1)
{"type": "SetRemove", "base": <set>, "item": <expr>}
```

### Deque Mutation (v1.1)

```json
// Add to back
{"type": "PushBack", "base": <deque>, "value": <expr>}

// Add to front
{"type": "PushFront", "base": <deque>, "value": <expr>}

// Remove from front (assigns to target variable)
{"type": "PopFront", "base": <deque>, "target": "varName"}

// Remove from back (assigns to target variable)
{"type": "PopBack", "base": <deque>, "target": "varName"}
```

### Heap Mutation (v1.1)

```json
// Push to heap
{"type": "HeapPush", "base": <heap>, "value": <expr>}

// Pop minimum (assigns to target variable)
{"type": "HeapPop", "base": <heap>, "target": "varName"}
```

### Regex Mutation (v1.3)

```json
// Replace matches
{"type": "RegexReplace", "pattern": <string>, "text": <string>, "replacement": <string>, "target": "varName"}

// Split by pattern
{"type": "RegexSplit", "pattern": <string>, "text": <string>, "target": "varName"}
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

### Loop Control (v1.7)

```json
// Break out of loop
{"type": "Break"}

// Skip to next iteration
{"type": "Continue"}
```

### Exception Handling (v1.8)

```json
// Throw an error
{"type": "Throw", "message": <expr>}

// Try/catch/finally
{
  "type": "TryCatch",
  "body": [<statement>, ...],
  "catch_var": "e",
  "catch_body": [<statement>, ...],
  "finally_body": [<statement>, ...]  // optional
}
```

- Catches both `Throw` and runtime errors (division by zero, etc.)
- `catch_var` receives the error message as a string
- `finally_body` always executes
- Return/Break/Continue propagate through (NOT caught)

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

### Set Deduplication (v1.1)

```json
{
  "type": "Let", "name": "seen", "value": {"type": "Set", "items": []}
},
{
  "type": "ForEach",
  "var": "item",
  "iter": {"type": "Var", "name": "arr"},
  "body": [
    {"type": "SetAdd", "base": {"type": "Var", "name": "seen"}, "item": {"type": "Var", "name": "item"}}
  ]
}
```

### BFS with Deque (v1.1)

```json
{
  "type": "Let", "name": "queue", "value": {"type": "DequeNew"}
},
{
  "type": "PushBack", "base": {"type": "Var", "name": "queue"}, "value": {"type": "Var", "name": "start"}
},
{
  "type": "While",
  "test": {"type": "Binary", "op": ">", "left": {"type": "DequeSize", "base": {"type": "Var", "name": "queue"}}, "right": {"type": "Literal", "value": 0}},
  "body": [
    {"type": "PopFront", "base": {"type": "Var", "name": "queue"}, "target": "current"}
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

### Negative Indexing (v1.5)

```json
// Get last element
{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": -1}}

// Get second to last
{"type": "Index", "base": {"type": "Var", "name": "arr"}, "index": {"type": "Literal", "value": -2}}
```

### Slicing (v1.5)

```json
// Get first 3 elements
{"type": "Slice", "base": {"type": "Var", "name": "arr"}, "start": {"type": "Literal", "value": 0}, "end": {"type": "Literal", "value": 3}}

// Get elements from index 2 to end
{"type": "Slice", "base": {"type": "Var", "name": "arr"}, "start": {"type": "Literal", "value": 2}, "end": {"type": "Length", "base": {"type": "Var", "name": "arr"}}}
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

- **Mutable**: Arrays (list), Dictionaries (dict), Records, Sets, Deques, Heaps
- **Immutable**: Tuples, Literals

### Dictionary Keys

- Keys maintain **insertion order** (Python 3.7+)
- Keys are **not sorted**
- Supports **mixed-type keys** (e.g., tuples with integers and strings)

### Type Checking

All type checks happen at **runtime**:
- Index requires array/tuple and integer (can be negative in v1.5)
- Binary operators require compatible types
- Dictionary operations require dictionaries

---

## CLI Commands

```bash
# Run Core IL interpreter
python -m english_compiler run program.coreil.json

# Compile to Python
python -m english_compiler compile --target python --frontend mock program.txt

# Compile to JavaScript
python -m english_compiler compile --target javascript --frontend claude program.txt

# Compile to C++
python -m english_compiler compile --target cpp --frontend openai program.txt

# Force regeneration
python -m english_compiler compile --regen program.txt

# Run tests
python -m tests.run
python -m tests.run_algorithms
```

---

## Resources

- **[coreil_v1.md](coreil_v1.md)** - Complete specification
- **[examples/](examples/)** - Working programs
- **[STATUS.md](STATUS.md)** - Project status
- **[MIGRATION.md](MIGRATION.md)** - Upgrade guide

---

**Core IL v1.8 - Stable and Production Ready**
