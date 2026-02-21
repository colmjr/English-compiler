# Core IL v1.0-v1.11 Specification

**Version:** 1.0-1.11
**Status:** Stable
**Date:** 2026-02-15

---

## Philosophy

Core IL is the **semantic heart** of the English compiler. It is a closed, deterministic intermediate representation that separates language understanding from execution.

### Design Principles

1. **Determinism**: Core IL semantics are completely deterministic. Given the same Core IL program, all backends must produce identical results.

2. **Closed World**: Core IL is a sealed specification. All valid operations are explicitly defined. LLMs cannot invent helper functions or extend the IR.

3. **Separation of Concerns**:
   - **Frontend (LLM)**: Translates English/pseudocode → Core IL. This is the only non-deterministic step.
   - **Core IL**: Defines program semantics as structured JSON. This is cached and reused.
   - **Backends**: Interpret or compile Core IL deterministically (interpreter, Python, JavaScript, C++).

4. **Primitive-First**: Common operations are expressed using explicit primitives rather than library functions. This ensures backends can optimize and reason about code structure.

5. **Type Safety (Runtime)**: While Core IL doesn't have static types, operations validate their inputs at runtime and produce clear error messages.

### Version History

- **v1.11**: Added Ternary (conditional expression), StringFormat (string interpolation)
- **v1.8**: Added Throw, TryCatch (exception handling with try/catch/finally)
- **v1.7**: Added Break, Continue (loop control flow)
- **v1.6**: Added MethodCall, PropertyGet (Tier 2, OOP-style), WASM backend
- **v1.5**: Added Slice, Not (unary), negative indexing
- **v1.4**: Added ExternalCall, expanded string operations, JavaScript and C++ backends
- **v1.3**: Added JSON operations (JsonParse, JsonStringify) and Regex operations
- **v1.2**: Added Math, MathPow, MathConst for portable math operations
- **v1.1**: Added Record, Set, Deque, Heap, basic string operations
- **v1.0**: Formalized specification with short-circuit evaluation for logical operators (frozen)
- **v0.5**: Sealed the IL by adding explicit primitives (GetDefault, Keys, Push, Tuple)
- **v0.3**: Added function definitions and return statements
- **v0.2**: Added arrays and indexing support
- **v0.1**: Initial release with basic expressions, statements, and control flow

---

## Document Structure

Core IL programs are JSON documents with this top-level structure:

```json
{
  "version": "coreil-1.11",
  "ambiguities": [],
  "body": [<statement>, <statement>, ...]
}
```

### Fields

- **version** (string, required): Current version is `"coreil-1.11"`. Backward compatibility is maintained for all versions from `"coreil-0.1"` through `"coreil-1.7"`.

- **ambiguities** (array, optional): A list of ambiguity objects documenting places where the LLM made interpretation choices.

- **body** (array, required): The top-level statements of the program, executed in order.

---

## Expressions (v1.0 Core)

### Literal

Represents a constant value.

```json
{"type": "Literal", "value": 42}
{"type": "Literal", "value": "hello"}
{"type": "Literal", "value": true}
{"type": "Literal", "value": null}
```

### Var

References a variable by name.

```json
{"type": "Var", "name": "x"}
```

### Binary

Binary operations with short-circuit evaluation for `and`/`or`.

```json
{"type": "Binary", "op": "+", "left": <expr>, "right": <expr>}
```

Operators: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `and`, `or`

### Array

Creates an array (list).

```json
{"type": "Array", "items": [<expr>, ...]}
```

### Tuple

Creates an immutable tuple.

```json
{"type": "Tuple", "items": [<expr>, ...]}
```

### Map

Creates an empty dictionary.

```json
{"type": "Map", "items": []}
```

### Index

Accesses an element by index. Supports negative indexing in v1.5+.

```json
{"type": "Index", "base": <expr>, "index": <expr>}
```

### Length

Gets the length of an array or tuple.

```json
{"type": "Length", "base": <expr>}
```

### Get

Retrieves a value from a dictionary.

```json
{"type": "Get", "base": <expr>, "key": <expr>}
```

### GetDefault

Dictionary lookup with fallback.

```json
{"type": "GetDefault", "base": <expr>, "key": <expr>, "default": <expr>}
```

### Keys

Gets all keys from a dictionary (insertion order).

```json
{"type": "Keys", "base": <expr>}
```

### Range

Integer range for iteration (used in For loops).

```json
{"type": "Range", "from": <expr>, "to": <expr>, "inclusive": false}
```

### Call

Calls a user-defined function.

```json
{"type": "Call", "name": "func_name", "args": [<expr>, ...]}
```

---

## Expressions (v1.1-v1.5 Extensions)

### Not (v1.5)

Unary logical negation.

```json
{"type": "Not", "value": <expr>}
```

### Slice (v1.5)

Extracts a sublist.

```json
{"type": "Slice", "base": <expr>, "start": <expr>, "end": <expr>}
```

### Record (v1.1)

Creates a mutable record with named fields.

```json
{"type": "Record", "fields": {"x": <expr>, "y": <expr>}}
```

### GetField (v1.1)

Accesses a record field.

```json
{"type": "GetField", "base": <expr>, "field": "fieldName"}
```

### Set (v1.1)

Creates a set data structure.

```json
{"type": "Set", "items": [<expr>, ...]}
```

### SetHas (v1.1)

Checks set membership.

```json
{"type": "SetHas", "base": <expr>, "item": <expr>}
```

### SetSize (v1.1)

Gets set size.

```json
{"type": "SetSize", "base": <expr>}
```

### DequeNew (v1.1)

Creates an empty deque.

```json
{"type": "DequeNew"}
```

### DequeSize (v1.1)

Gets deque size.

```json
{"type": "DequeSize", "base": <expr>}
```

### HeapNew (v1.1)

Creates an empty min-heap.

```json
{"type": "HeapNew"}
```

### HeapSize (v1.1)

Gets heap size.

```json
{"type": "HeapSize", "base": <expr>}
```

### HeapPeek (v1.1)

Views the minimum element.

```json
{"type": "HeapPeek", "base": <expr>}
```

### String Operations (v1.1)

```json
{"type": "StringLength", "base": <expr>}
{"type": "Substring", "base": <expr>, "start": <expr>, "end": <expr>}
{"type": "CharAt", "base": <expr>, "index": <expr>}
{"type": "Join", "items": <expr>, "separator": <expr>}
```

### String Operations (v1.4)

```json
{"type": "StringSplit", "base": <expr>, "separator": <expr>}
{"type": "StringTrim", "base": <expr>}
{"type": "StringUpper", "base": <expr>}
{"type": "StringLower", "base": <expr>}
{"type": "StringReplace", "base": <expr>, "old": <expr>, "new": <expr>}
{"type": "StringContains", "base": <expr>, "substring": <expr>}
{"type": "StringStartsWith", "base": <expr>, "prefix": <expr>}
{"type": "StringEndsWith", "base": <expr>, "suffix": <expr>}
```

### Math Operations (v1.2)

```json
{"type": "Math", "op": "sqrt", "value": <expr>}  // sin, cos, tan, sqrt, floor, ceil, abs, log, exp
{"type": "MathPow", "base": <expr>, "exponent": <expr|}
{"type": "MathConst", "name": "pi"}  // pi, e
```

### JSON Operations (v1.3)

```json
{"type": "JsonParse", "value": <expr>}
{"type": "JsonStringify", "value": <expr>}
```

### Regex Operations (v1.3)

```json
{"type": "RegexMatch", "pattern": <expr>, "text": <expr>}
{"type": "RegexFindAll", "pattern": <expr>, "text": <expr>}
```

### ExternalCall (v1.4, Tier 2)

Platform-specific calls. Only supported in Python backend.

```json
{"type": "ExternalCall", "module": "time", "function": "time", "args": []}
```

Available modules: `time`, `os`, `fs`, `http`, `crypto`

---

## Expressions (v1.11)

### Ternary (v1.11)

Short-circuit conditional expression. Evaluates `test`, then evaluates and returns either `consequent` (if truthy) or `alternate` (if falsy). Only the chosen branch is evaluated.

```json
{"type": "Ternary", "test": <expr>, "consequent": <expr>, "alternate": <expr>}
```

**Fields:**

- `test` (expression, required): The condition to evaluate.
- `consequent` (expression, required): Returned when `test` is truthy. Only evaluated if chosen.
- `alternate` (expression, required): Returned when `test` is falsy. Only evaluated if chosen.

**Example** -- assign the smaller of two values:

```json
{
  "type": "Ternary",
  "test": {"type": "Binary", "op": "<", "left": {"type": "Var", "name": "a"}, "right": {"type": "Var", "name": "b"}},
  "consequent": {"type": "Var", "name": "a"},
  "alternate": {"type": "Var", "name": "b"}
}
```

**Semantics:**
- Short-circuit: only one of `consequent` / `alternate` is evaluated, never both.
- Can be nested (the result is an expression, usable anywhere an expression is expected).

### StringFormat (v1.11)

Evaluates each part expression, converts each result to its string representation, and concatenates them into a single string. This is the Core IL equivalent of string interpolation / f-strings.

```json
{"type": "StringFormat", "parts": [<expr>, ...]}
```

**Fields:**

- `parts` (array of expressions, required): One or more expressions. Each is evaluated in order, converted to a string, and concatenated.

**Example** -- build a greeting message:

```json
{
  "type": "StringFormat",
  "parts": [
    {"type": "Literal", "value": "Hello, "},
    {"type": "Var", "name": "name"},
    {"type": "Literal", "value": "! You are "},
    {"type": "Var", "name": "age"},
    {"type": "Literal", "value": " years old."}
  ]
}
```

**Semantics:**
- Each part is evaluated left-to-right.
- Non-string values are converted to their string representation (integers, floats, booleans, null, arrays, etc.).
- An empty `parts` array produces an empty string `""`.

---

## Statements (v1.0 Core)

### Let

Declares a variable.

```json
{"type": "Let", "name": "x", "value": <expr>}
```

### Assign

Updates a variable.

```json
{"type": "Assign", "name": "x", "value": <expr>}
```

### SetIndex

Updates an array element.

```json
{"type": "SetIndex", "base": <expr>, "index": <expr>, "value": <expr>}
```

### Set (Statement)

Sets a dictionary key-value pair.

```json
{"type": "Set", "base": <expr>, "key": <expr>, "value": <expr>}
```

### Push

Appends to an array.

```json
{"type": "Push", "base": <expr>, "value": <expr>}
```

### Print

Outputs to stdout.

```json
{"type": "Print", "args": [<expr>, ...]}
```

### If

Conditional execution.

```json
{"type": "If", "test": <expr>, "then": [<stmt>, ...], "else": [<stmt>, ...]}
```

### While

Loop with condition.

```json
{"type": "While", "test": <expr>, "body": [<stmt>, ...]}
```

### For

Range iteration.

```json
{"type": "For", "var": "i", "iter": <Range>, "body": [<stmt>, ...]}
```

### ForEach

Collection iteration.

```json
{"type": "ForEach", "var": "item", "iter": <expr>, "body": [<stmt>, ...]}
```

### FuncDef

Function definition.

```json
{"type": "FuncDef", "name": "func", "params": ["a", "b"], "body": [<stmt>, ...]}
```

### Return

Returns from function.

```json
{"type": "Return", "value": <expr>}
```

---

## Statements (v1.1-v1.5 Extensions)

### SetField (v1.1)

Updates a record field.

```json
{"type": "SetField", "base": <expr>, "field": "name", "value": <expr>}
```

### SetAdd (v1.1)

Adds to a set.

```json
{"type": "SetAdd", "base": <expr>, "item": <expr>}
```

### SetRemove (v1.1)

Removes from a set.

```json
{"type": "SetRemove", "base": <expr>, "item": <expr>}
```

### Deque Operations (v1.1)

```json
{"type": "PushBack", "base": <expr>, "value": <expr>}
{"type": "PushFront", "base": <expr>, "value": <expr>}
{"type": "PopFront", "base": <expr>, "target": "varName"}
{"type": "PopBack", "base": <expr>, "target": "varName"}
```

### Heap Operations (v1.1)

```json
{"type": "HeapPush", "base": <expr>, "value": <expr>}
{"type": "HeapPop", "base": <expr>, "target": "varName"}
```

### Regex Operations (v1.3)

```json
{"type": "RegexReplace", "pattern": <expr>, "text": <expr>, "replacement": <expr>, "target": "varName"}
{"type": "RegexSplit", "pattern": <expr>, "text": <expr>, "target": "varName"}
```

### MethodCall (v1.6, Tier 2)

Calls a method on an object. Non-portable — not supported in the interpreter.

```json
{"type": "MethodCall", "object": <expr>, "method": "fit", "args": [<expr>, ...]}
```

### PropertyGet (v1.6, Tier 2)

Accesses a property on an object. Non-portable.

```json
{"type": "PropertyGet", "object": <expr>, "property": "coef_"}
```

### Break (v1.7)

Exits the innermost loop immediately.

```json
{"type": "Break"}
```

Only valid inside While, For, or ForEach loops.

### Continue (v1.7)

Skips to the next iteration of the innermost loop.

```json
{"type": "Continue"}
```

Only valid inside While, For, or ForEach loops.

### Throw (v1.8)

Raises a runtime error with a message.

```json
{"type": "Throw", "message": <expr>}
```

The message expression must evaluate to a string. If thrown outside of a TryCatch, it crashes the program.

### TryCatch (v1.8)

Exception handling with try/catch/finally.

```json
{
  "type": "TryCatch",
  "body": [<stmt>, ...],
  "catch_var": "e",
  "catch_body": [<stmt>, ...],
  "finally_body": [<stmt>, ...]
}
```

- `body` (required): Statements to try
- `catch_var` (required): Variable name that receives the error message as a string
- `catch_body` (required): Statements to execute on error
- `finally_body` (optional): Statements that always execute, even if catch re-throws

Catches both explicit `Throw` errors and runtime errors (division by zero, index out of bounds, etc.). Control flow signals (Return, Break, Continue) are NOT caught — they propagate through.

---

## Key Semantics

### Short-Circuit Evaluation

`and` and `or` operators MUST short-circuit:
- `and`: Returns `false` without evaluating right if left is falsy
- `or`: Returns `true` without evaluating right if left is truthy

### Negative Indexing (v1.5)

Arrays support negative indices: `-1` is last element, `-2` is second-to-last, etc.

### Type Checking

All type checks happen at runtime with clear error messages.

### Recursion Limit

Maximum call depth: 100

### Dictionary Ordering

Keys maintain insertion order.

---

## Backends

- **Interpreter**: Direct execution (Python)
- **Python Codegen**: Transpiles to Python 3.10+
- **JavaScript Codegen**: Transpiles to ES6+
- **C++ Codegen**: Transpiles to C++17
- **Rust Codegen**: Transpiles to Rust
- **Go Codegen**: Transpiles to Go
- **WASM Codegen**: Transpiles to AssemblyScript (compiled to WebAssembly)

All backends produce identical output.

---

## Frontends

- **Claude**: Anthropic's Claude models
- **OpenAI**: GPT-4 and GPT-4o
- **Gemini**: Google's Gemini models
- **Qwen**: Alibaba's Qwen models
- **Mock**: Deterministic mock for testing

---

## Stability Guarantee

**Core IL v1.0 is stable and frozen.**

- v1.0 semantics will never change
- v1.1-v1.11 add features without breaking v1.0
- Full backward compatibility maintained

---

## Conclusion

Core IL v1.11 provides a complete, deterministic IR for the English compiler. The specification is complete, closed, deterministic, tested, and documented.
