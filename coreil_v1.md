# Core IL v1.0 Specification

**Version:** 1.0
**Status:** Stable
**Date:** 2026-01-10

---

## Philosophy

Core IL is the **semantic heart** of the English compiler. It is a closed, deterministic intermediate representation that separates language understanding from execution.

### Design Principles

1. **Determinism**: Core IL semantics are completely deterministic. Given the same Core IL program, all backends must produce identical results.

2. **Closed World**: Core IL is a sealed specification. All valid operations are explicitly defined. LLMs cannot invent helper functions or extend the IR.

3. **Separation of Concerns**:
   - **Frontend (LLM)**: Translates English/pseudocode → Core IL. This is the only non-deterministic step.
   - **Core IL**: Defines program semantics as structured JSON. This is cached and reused.
   - **Backends**: Interpret or compile Core IL deterministically (interpreter, Python codegen, etc.).

4. **Primitive-First**: Common operations are expressed using explicit primitives rather than library functions. This ensures backends can optimize and reason about code structure.

5. **Type Safety (Runtime)**: While Core IL doesn't have static types, operations validate their inputs at runtime and produce clear error messages.

### Version History

- **v0.1**: Initial release with basic expressions, statements, and control flow
- **v0.2**: Added arrays and indexing support
- **v0.3**: Added function definitions and return statements
- **v0.4**: (unused version number)
- **v0.5**: Sealed the IL by adding explicit primitives (GetDefault, Keys, Push, Tuple) and restricting Call nodes
- **v1.0**: Formalized specification with short-circuit evaluation for logical operators

---

## Document Structure

Core IL programs are JSON documents with this top-level structure:

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [<statement>, <statement>, ...]
}
```

### Fields

- **version** (string, required): Must be `"coreil-1.0"` for this specification. Backward compatibility is maintained for `"coreil-0.1"` through `"coreil-0.5"`.

- **ambiguities** (array, optional): A list of ambiguity objects documenting places where the LLM made interpretation choices. Used for debugging and user feedback. Each ambiguity object should have fields like `location`, `choices`, and `chosen`.

- **body** (array, required): The top-level statements of the program, executed in order.

---

## Node Types

Core IL consists of two categories: **expressions** (evaluate to values) and **statements** (perform actions).

---

## Expressions

Expressions evaluate to values. They can appear as:
- Right-hand side of assignments
- Arguments to function calls
- Test conditions in If/While
- Elements in arrays/tuples
- Operands in binary operations

### Literal

**Purpose**: Represents a constant value.

**Shape**:
```json
{
  "type": "Literal",
  "value": <any JSON value>
}
```

**Semantics**:
- Evaluates to the literal value provided.
- `value` can be: number, string, boolean, null.
- Examples: `42`, `"hello"`, `true`, `null`, `3.14`.

**Invariants**:
- `value` field is required.

---

### Var

**Purpose**: References a variable by name.

**Shape**:
```json
{
  "type": "Var",
  "name": "variable_name"
}
```

**Semantics**:
- Looks up the variable `name` in the current scope.
- Variables are resolved in local scope (function parameters/locals) first, then global scope.
- Raises error if the variable is not defined.

**Invariants**:
- `name` must be a non-empty string.

---

### Binary

**Purpose**: Binary operations on two operands.

**Shape**:
```json
{
  "type": "Binary",
  "op": "<operator>",
  "left": <expr>,
  "right": <expr>
}
```

**Semantics**:
- Applies the binary operator `op` to `left` and `right` operands.
- **Short-circuit evaluation**: For `and` and `or` operators, the right operand is only evaluated if necessary:
  - `and`: If left is falsy, returns `false` without evaluating right.
  - `or`: If left is truthy, returns `true` without evaluating right.
- For all other operators, both operands are evaluated before applying the operation.

**Operators**:
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparison: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical: `and`, `or`

**Type Requirements**:
- Arithmetic operators require numeric operands.
- Comparison operators work on comparable types (numbers, strings, booleans).
- Logical operators coerce operands to boolean values.

**Invariants**:
- `op` must be one of the listed operators.
- `left` and `right` must be valid expressions.

---

### Array

**Purpose**: Creates an array (list) of values.

**Shape**:
```json
{
  "type": "Array",
  "items": [<expr>, <expr>, ...]
}
```

**Semantics**:
- Evaluates each expression in `items` and returns a list containing those values.
- Empty array: `{"type": "Array", "items": []}`.
- Arrays are mutable and can be modified using SetIndex and Push operations.

**Invariants**:
- `items` must be an array (can be empty).
- Each item must be a valid expression.

---

### Index

**Purpose**: Accesses an element in an array or tuple by index.

**Shape**:
```json
{
  "type": "Index",
  "base": <expr>,
  "index": <expr>
}
```

**Semantics**:
- Evaluates `base` to get an array or tuple.
- Evaluates `index` to get a non-negative integer.
- Returns the element at position `index` (0-based).
- Raises error if index is out of range.

**Type Requirements**:
- `base` must evaluate to an array (list) or tuple.
- `index` must evaluate to a non-negative integer.

**Invariants**:
- Both `base` and `index` are required.
- Index bounds are checked at runtime.

---

### Length

**Purpose**: Gets the length of an array or tuple.

**Shape**:
```json
{
  "type": "Length",
  "base": <expr>
}
```

**Semantics**:
- Evaluates `base` to get an array or tuple.
- Returns the number of elements as an integer.

**Type Requirements**:
- `base` must evaluate to an array (list) or tuple.

**Invariants**:
- `base` is required.

---

### Tuple

**Purpose**: Creates an immutable tuple of values.

**Shape**:
```json
{
  "type": "Tuple",
  "items": [<expr>, <expr>, ...]
}
```

**Semantics**:
- Evaluates each expression in `items` and returns a tuple containing those values.
- Tuples are immutable but can be indexed using Index.
- Tuples can contain mixed types.
- Empty tuple: `{"type": "Tuple", "items": []}`.

**Use Cases**:
- Representing pairs or structured data (e.g., bigram pairs in BPE).
- Dictionary keys that need multiple values.
- Return multiple values from expressions.

**Invariants**:
- `items` must be an array (can be empty).
- Each item must be a valid expression.

---

### Map

**Purpose**: Creates an empty dictionary (hash map).

**Shape**:
```json
{
  "type": "Map",
  "items": []
}
```

**Semantics**:
- Returns an empty dictionary.
- Dictionaries are mutable and can be modified using Set operations.
- Keys can be any hashable value (numbers, strings, tuples).
- In Python 3.7+, dictionaries maintain insertion order.

**Invariants**:
- `items` must be an empty array (future versions might support non-empty initialization).

---

### Get

**Purpose**: Retrieves a value from a dictionary by key.

**Shape**:
```json
{
  "type": "Get",
  "base": <expr>,
  "key": <expr>
}
```

**Semantics**:
- Evaluates `base` to get a dictionary.
- Evaluates `key` to get the lookup key.
- Returns the value associated with `key`.
- Raises error if key is not present.

**Type Requirements**:
- `base` must evaluate to a dictionary.
- `key` must be hashable.

**Invariants**:
- Both `base` and `key` are required.
- Key must exist in the dictionary.

---

### GetDefault

**Purpose**: Retrieves a value from a dictionary with a default fallback.

**Shape**:
```json
{
  "type": "GetDefault",
  "base": <expr>,
  "key": <expr>,
  "default": <expr>
}
```

**Semantics**:
- Evaluates `base` to get a dictionary.
- Evaluates `key` to get the lookup key.
- If key exists, returns the associated value.
- If key does not exist, returns the result of evaluating `default`.
- Does not modify the dictionary.

**Type Requirements**:
- `base` must evaluate to a dictionary.
- `key` must be hashable.

**Invariants**:
- All three fields (`base`, `key`, `default`) are required.

---

### Keys

**Purpose**: Gets all keys from a dictionary.

**Shape**:
```json
{
  "type": "Keys",
  "base": <expr>
}
```

**Semantics**:
- Evaluates `base` to get a dictionary.
- Returns a list of all keys in the dictionary.
- Key order follows dictionary insertion order (Python 3.7+).
- Does not sort keys (to support mixed-type keys like tuples containing integers and strings).

**Type Requirements**:
- `base` must evaluate to a dictionary.

**Invariants**:
- `base` is required.

---

### Range

**Purpose**: Represents an integer range for iteration.

**Shape**:
```json
{
  "type": "Range",
  "from": <expr>,
  "to": <expr>,
  "inclusive": <boolean>
}
```

**Semantics**:
- Evaluates `from` to get the start integer (inclusive).
- Evaluates `to` to get the end integer.
- If `inclusive` is `false`, range is [from, to).
- If `inclusive` is `true`, range is [from, to].
- Used exclusively in For loops.

**Type Requirements**:
- Both `from` and `to` must evaluate to integers.

**Invariants**:
- All three fields are required.
- Only valid as the `iter` field in a For statement.

---

### Call

**Purpose**: Calls a user-defined function.

**Shape**:
```json
{
  "type": "Call",
  "name": "<function_name>",
  "args": [<expr>, <expr>, ...]
}
```

**Semantics**:
- Looks up the function `name` defined by a FuncDef statement.
- Evaluates each argument expression in order.
- Binds arguments to function parameters.
- Executes the function body.
- Returns the value from a Return statement, or `null` if no Return is executed.
- Supports recursion with a maximum call depth of 100.

**Restrictions** (v1.0):
- Cannot call built-in helper functions (these were removed in v0.5).
- Only user-defined functions from FuncDef are callable.
- Disallowed helper calls: `get_or_default`, `keys`, `append`, `entries`.

**Type Requirements**:
- `name` must match a defined function.
- Number of arguments must match function's parameter count.

**Invariants**:
- `name` must be a non-empty string.
- `args` must be an array.
- Function must be defined before it's called.

---

## Statements

Statements perform actions and do not return values. They can:
- Declare and assign variables
- Modify data structures
- Control program flow
- Define functions
- Print output

### Let

**Purpose**: Declares and initializes a new variable.

**Shape**:
```json
{
  "type": "Let",
  "name": "variable_name",
  "value": <expr>
}
```

**Semantics**:
- Evaluates `value` expression.
- Creates a new variable `name` with the evaluated value.
- Variable is added to the current scope (global or local).
- If variable already exists, this shadows it (creates a new binding).

**Scope Rules**:
- Inside a function: variable is local to that function.
- Outside a function: variable is global.

**Invariants**:
- `name` must be a non-empty string.
- `value` must be a valid expression.

---

### Assign

**Purpose**: Updates an existing variable's value.

**Shape**:
```json
{
  "type": "Assign",
  "name": "variable_name",
  "value": <expr>
}
```

**Semantics**:
- Evaluates `value` expression.
- Updates the existing variable `name` with the new value.
- Looks up variable in local scope first, then global scope.
- Raises error if variable is not defined.

**Invariants**:
- `name` must be a non-empty string.
- `value` must be a valid expression.
- Variable must already exist.

---

### SetIndex

**Purpose**: Updates an element in an array by index.

**Shape**:
```json
{
  "type": "SetIndex",
  "base": <expr>,
  "index": <expr>,
  "value": <expr>
}
```

**Semantics**:
- Evaluates `base` to get an array.
- Evaluates `index` to get a non-negative integer.
- Evaluates `value` to get the new value.
- Mutates the array by setting `array[index] = value`.
- Raises error if index is out of range.

**Type Requirements**:
- `base` must evaluate to an array (list), not a tuple (tuples are immutable).
- `index` must evaluate to a non-negative integer.

**Invariants**:
- All three fields are required.
- Index bounds are checked at runtime.

---

### Set

**Purpose**: Sets a key-value pair in a dictionary.

**Shape**:
```json
{
  "type": "Set",
  "base": <expr>,
  "key": <expr>,
  "value": <expr>
}
```

**Semantics**:
- Evaluates `base` to get a dictionary.
- Evaluates `key` to get the key.
- Evaluates `value` to get the value.
- Mutates the dictionary by setting `dict[key] = value`.
- Creates the key if it doesn't exist, or updates it if it does.

**Type Requirements**:
- `base` must evaluate to a dictionary.
- `key` must be hashable.

**Invariants**:
- All three fields are required.

---

### Push

**Purpose**: Appends a value to the end of an array.

**Shape**:
```json
{
  "type": "Push",
  "base": <expr>,
  "value": <expr>
}
```

**Semantics**:
- Evaluates `base` to get an array.
- Evaluates `value` to get the value to append.
- Mutates the array by appending the value to the end.
- Equivalent to Python's `list.append()`.

**Type Requirements**:
- `base` must evaluate to an array (list).

**Invariants**:
- Both `base` and `value` are required.

---

### Print

**Purpose**: Outputs values to standard output.

**Shape**:
```json
{
  "type": "Print",
  "args": [<expr>, <expr>, ...]
}
```

**Semantics**:
- Evaluates each expression in `args` in order.
- Prints each value to standard output.
- If multiple args, prints them space-separated on one line.
- If single arg, prints just that value.
- Automatically adds a newline at the end.

**Output Format**:
- Uses Python's `print()` representation.
- Lists: `[1, 2, 3]`
- Dicts: `{(1, 2): 'r1', (20, 10): 'r2'}`
- Strings: Printed without quotes unless in a container.

**Invariants**:
- `args` must be an array (can be empty, prints blank line).

---

### If

**Purpose**: Conditional execution.

**Shape**:
```json
{
  "type": "If",
  "test": <expr>,
  "then": [<statement>, ...],
  "else": [<statement>, ...]
}
```

**Semantics**:
- Evaluates `test` expression.
- If test is truthy, executes statements in `then` block.
- If test is falsy and `else` exists, executes statements in `else` block.
- If test is falsy and `else` is omitted, does nothing.

**Truthiness**:
- Truthy: non-zero numbers, non-empty strings, non-empty arrays, `true`.
- Falsy: `0`, `""`, `[]`, `{}`, `null`, `false`.

**Invariants**:
- `test` must be a valid expression.
- `then` must be an array of statements.
- `else` is optional; if present, must be an array of statements.

---

### While

**Purpose**: Loop with a condition.

**Shape**:
```json
{
  "type": "While",
  "test": <expr>,
  "body": [<statement>, ...]
}
```

**Semantics**:
- Evaluates `test` expression.
- If test is truthy, executes statements in `body`, then re-evaluates test.
- Repeats until test becomes falsy.
- If test is initially falsy, body never executes.

**Invariants**:
- `test` must be a valid expression.
- `body` must be an array of statements.

---

### For

**Purpose**: Iterates over an integer range.

**Shape**:
```json
{
  "type": "For",
  "var": "loop_variable",
  "iter": <Range>,
  "body": [<statement>, ...]
}
```

**Semantics**:
- `iter` must be a Range expression.
- Creates a new loop variable `var` in the loop's scope.
- Iterates through the range, executing `body` with `var` set to each value.
- Loop variable is scoped to the loop body.

**Example**:
```json
{
  "type": "For",
  "var": "i",
  "iter": {
    "type": "Range",
    "from": {"type": "Literal", "value": 0},
    "to": {"type": "Literal", "value": 10},
    "inclusive": false
  },
  "body": [...]
}
```
Iterates `i` from 0 to 9.

**Invariants**:
- `var` must be a non-empty string.
- `iter` must be a Range expression.
- `body` must be an array of statements.

---

### ForEach

**Purpose**: Iterates over elements in an array or keys in a dictionary.

**Shape**:
```json
{
  "type": "ForEach",
  "var": "loop_variable",
  "iter": <expr>,
  "body": [<statement>, ...]
}
```

**Semantics**:
- Evaluates `iter` to get an array or Keys expression result.
- Creates a new loop variable `var` in the loop's scope.
- Iterates through the collection, executing `body` with `var` set to each element.

**Common Patterns**:
- Iterate array elements: `iter` is an array expression or variable.
- Iterate dictionary keys: `iter` is a Keys expression.

**Example** (iterate array):
```json
{
  "type": "ForEach",
  "var": "item",
  "iter": {"type": "Var", "name": "my_array"},
  "body": [...]
}
```

**Example** (iterate dict keys):
```json
{
  "type": "ForEach",
  "var": "key",
  "iter": {
    "type": "Keys",
    "base": {"type": "Var", "name": "my_dict"}
  },
  "body": [...]
}
```

**Invariants**:
- `var` must be a non-empty string.
- `iter` must be a valid expression (typically array, variable, or Keys).
- `body` must be an array of statements.

---

### FuncDef

**Purpose**: Defines a named function.

**Shape**:
```json
{
  "type": "FuncDef",
  "name": "function_name",
  "params": ["param1", "param2", ...],
  "body": [<statement>, ...]
}
```

**Semantics**:
- Defines a function named `name` with parameters `params`.
- Function body is a list of statements.
- Parameters become local variables when the function is called.
- Function can be called using Call expressions.
- Functions can call themselves (recursion) up to depth 100.
- If no Return statement is executed, function returns `null`.

**Scope**:
- Function definitions are global (even if defined inside another function).
- Parameters and local Let variables are scoped to the function body.

**Invariants**:
- `name` must be a non-empty string.
- `params` must be an array of strings (can be empty for zero-parameter functions).
- `body` must be an array of statements.
- Parameter names must be unique.

---

### Return

**Purpose**: Returns a value from a function.

**Shape**:
```json
{
  "type": "Return",
  "value": <expr>
}
```

**Semantics**:
- Evaluates `value` expression.
- Immediately exits the current function with the evaluated value.
- Can only be used inside a function body.
- Raises error if used outside a function.

**Invariants**:
- `value` must be a valid expression.
- Must appear inside a FuncDef body.

---

## Implementation Notes

### Short-Circuit Evaluation

**Critical Feature**: The `and` and `or` operators MUST implement short-circuit evaluation to match Python semantics and prevent runtime errors.

**Why It Matters**:
Algorithms often use patterns like:
```json
{
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
    "left": {
      "type": "Index",
      "base": {"type": "Var", "name": "arr"},
      "index": {"type": "Var", "name": "i"}
    },
    "right": {"type": "Literal", "value": 0}
  }
}
```

This checks `i < len(arr) and arr[i] == 0`. Without short-circuiting, `arr[i]` would be evaluated even when `i >= len(arr)`, causing an index out of range error.

**Implementation**:
```python
# For 'and' operator:
left_value = eval_expr(left)
if not left_value:
    return False  # Don't evaluate right
return bool(eval_expr(right))

# For 'or' operator:
left_value = eval_expr(left)
if left_value:
    return True  # Don't evaluate right
return bool(eval_expr(right))
```

---

### Type Checking

Core IL performs runtime type checking:

- **Index**: base must be list or tuple, index must be non-negative integer
- **Length**: base must be list or tuple
- **Get/GetDefault**: base must be dictionary
- **Keys**: base must be dictionary
- **SetIndex**: base must be list (not tuple), index must be valid
- **Set**: base must be dictionary
- **Push**: base must be list
- **Binary operators**: operands must have compatible types

Error messages should clearly indicate:
1. What went wrong
2. What type was expected
3. What type was received

---

### Recursion Limits

To prevent infinite recursion:
- Maximum call depth: 100
- Each Call increments the depth counter
- Return decrements the depth counter
- Exceeding the limit raises: "call depth exceeded"

---

### Dictionary Key Ordering

Core IL dictionaries maintain **insertion order** (following Python 3.7+ semantics):

- Keys are returned by the Keys operation in insertion order
- This is deterministic and works with mixed-type keys
- Do NOT sort keys (would fail on mixed types like `(20, 10)` and `(1, "r1")`)

---

### Mutability

**Mutable Types**:
- Arrays (lists): Can be modified with SetIndex and Push
- Dictionaries: Can be modified with Set

**Immutable Types**:
- Tuples: Cannot be modified after creation
- Literals: Numbers, strings, booleans, null

**Implications**:
- SetIndex only works on arrays, not tuples
- Tuples are suitable for dictionary keys; arrays are not

---

## Example Programs

### Hello World

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [
    {
      "type": "Print",
      "args": [
        {"type": "Literal", "value": "Hello, World!"}
      ]
    }
  ]
}
```

---

### Array Sum

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [
    {
      "type": "Let",
      "name": "arr",
      "value": {
        "type": "Array",
        "items": [
          {"type": "Literal", "value": 1},
          {"type": "Literal", "value": 2},
          {"type": "Literal", "value": 3},
          {"type": "Literal", "value": 4},
          {"type": "Literal", "value": 5}
        ]
      }
    },
    {
      "type": "Let",
      "name": "sum",
      "value": {"type": "Literal", "value": 0}
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
    },
    {
      "type": "Print",
      "args": [{"type": "Var", "name": "sum"}]
    }
  ]
}
```

Output: `15`

---

### Fibonacci Function

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [
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
            {
              "type": "Return",
              "value": {"type": "Var", "name": "n"}
            }
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
                {
                  "type": "Binary",
                  "op": "-",
                  "left": {"type": "Var", "name": "n"},
                  "right": {"type": "Literal", "value": 1}
                }
              ]
            },
            "right": {
              "type": "Call",
              "name": "fib",
              "args": [
                {
                  "type": "Binary",
                  "op": "-",
                  "left": {"type": "Var", "name": "n"},
                  "right": {"type": "Literal", "value": 2}
                }
              ]
            }
          }
        }
      ]
    },
    {
      "type": "Print",
      "args": [
        {
          "type": "Call",
          "name": "fib",
          "args": [{"type": "Literal", "value": 10}]
        }
      ]
    }
  ]
}
```

Output: `55`

---

### Dictionary Word Count

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [
    {
      "type": "Let",
      "name": "words",
      "value": {
        "type": "Array",
        "items": [
          {"type": "Literal", "value": "hello"},
          {"type": "Literal", "value": "world"},
          {"type": "Literal", "value": "hello"},
          {"type": "Literal", "value": "foo"},
          {"type": "Literal", "value": "world"},
          {"type": "Literal", "value": "hello"}
        ]
      }
    },
    {
      "type": "Let",
      "name": "counts",
      "value": {"type": "Map", "items": []}
    },
    {
      "type": "ForEach",
      "var": "word",
      "iter": {"type": "Var", "name": "words"},
      "body": [
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
      ]
    },
    {
      "type": "Print",
      "args": [{"type": "Var", "name": "counts"}]
    }
  ]
}
```

Output: `{'hello': 3, 'world': 2, 'foo': 1}`

---

## Validation Rules

A valid Core IL document must satisfy:

1. **Version**: `version` field must be `"coreil-1.0"` (or backward-compatible versions).

2. **Structure**: Top-level must have `body` array.

3. **Node Types**: All nodes must have a `type` field with a recognized value.

4. **Type-Specific Rules**:
   - Expressions must not appear where statements are expected (except in specific fields like `value`, `test`, `args`).
   - Statements must not appear where expressions are expected.

5. **Required Fields**: Each node type must have all its required fields.

6. **Variable References**:
   - Var nodes must reference variables that exist in scope.
   - Assign must reference existing variables.

7. **Function Definitions**:
   - FuncDef creates a global function.
   - Call must reference defined functions (or be within the function's own body for recursion).
   - Return must appear inside a function body.

8. **Type Constraints**:
   - Binary operators must receive appropriate operand types.
   - Index must receive array/tuple and integer.
   - Dictionary operations must receive dictionaries.

9. **Disallowed Constructs**:
   - Cannot call helper functions: `get_or_default`, `keys`, `append`, `entries`.
   - Must use explicit primitives: GetDefault, Keys, Push, Tuple.

---

## Error Handling

Core IL interpreters and compilers should produce clear error messages:

### Expression Errors

- `"Var missing name"`: Var node lacks name field.
- `"Variable not defined: <name>"`: Referenced variable doesn't exist.
- `"Index must be a non-negative integer"`: Index is not an integer or is negative.
- `"Index base must be an array or tuple"`: Trying to index a non-indexable value.
- `"Index out of range"`: Index exceeds array/tuple length.
- `"Length base must be an array or tuple"`: Trying to get length of non-sequence.
- `"unsupported binary op: <op>"`: Unrecognized binary operator.

### Statement Errors

- `"Let missing name"`: Let node lacks name field.
- `"Variable not defined: <name>"`: Assign references undefined variable.
- `"Function not defined: <name>"`: Call references undefined function.
- `"call depth exceeded"`: Recursion depth > 100.
- `"Return outside function"`: Return statement not in function body.

### Type Errors

- `"expected number, got <type>"`: Arithmetic on non-numeric type.
- `"expected dict, got <type>"`: Dictionary operation on non-dict.
- `"expected list, got <type>"`: Array operation on non-array.

---

## Backend Requirements

Any Core IL backend (interpreter, compiler, transpiler) MUST:

1. **Implement All Node Types**: Support every node type in this specification.

2. **Maintain Semantics**: Produce the same results as the reference interpreter for all valid programs.

3. **Short-Circuit Evaluation**: Implement proper short-circuit for `and` and `or`.

4. **Preserve Ordering**: Maintain dictionary insertion order for Keys operation.

5. **Runtime Type Checking**: Validate types at runtime and produce clear errors.

6. **Recursion Limits**: Enforce maximum call depth of 100.

7. **Deterministic Output**: Given the same Core IL, produce identical output every time.

8. **Error Messages**: Provide helpful error messages that identify the problem clearly.

---

## Testing

Core IL implementations should be tested with:

1. **Unit Tests**: Each node type in isolation.
2. **Integration Tests**: Complete programs from the examples/ directory.
3. **Error Cases**: Invalid inputs should produce clear error messages.
4. **Equivalence Tests**: Interpreter output == Python codegen output for all test programs.
5. **Short-Circuit Tests**: Verify that `and`/`or` don't evaluate right side unnecessarily.

Test programs included in the repository:
- `examples/array_sum.coreil.json`
- `examples/bubble_sort.coreil.json`
- `examples/for_inclusive.coreil.json`
- `examples/for_sum.coreil.json`
- `testing.coreil.json` (BPE algorithm)

All tests must pass for both interpreter and Python codegen backends.

---

## Migration from v0.5

Core IL v1.0 is backward compatible with v0.5. The main changes:

1. **Version String**: Update `"version": "coreil-0.5"` to `"version": "coreil-1.0"`.

2. **No Syntax Changes**: All v0.5 programs are valid v1.0 programs.

3. **Formalized Semantics**: v1.0 explicitly documents short-circuit evaluation, which was implemented in late v0.5.

4. **Comprehensive Documentation**: This specification provides complete reference documentation.

### Upgrade Path

To upgrade a v0.5 program to v1.0:
1. Change version field to `"coreil-1.0"`
2. Validate against this specification
3. Test with interpreter and codegen
4. No code changes required

---

## Future Considerations

Core IL v1.0 is **stable and frozen**. Future versions might consider:

- **Type Annotations** (v2.0): Optional static type information for optimization.
- **Modules** (v2.0): Import/export system for code reuse.
- **String Operations** (v1.1): Substring, split, join primitives.
- **List Slicing** (v1.1): Slice notation for arrays.
- **Exception Handling** (v2.0): Try/catch for error recovery.
- **Iterators** (v2.0): Lazy evaluation for large sequences.

However, v1.0 is feature-complete for the current compiler goals and should remain stable for production use.

---

## Conclusion

Core IL v1.0 provides a complete, deterministic intermediate representation for the English compiler. It successfully bridges the gap between LLM-based natural language understanding and deterministic code execution.

The specification is:
- **Complete**: All necessary primitives are included
- **Closed**: No extension mechanism or helper functions
- **Deterministic**: Same input always produces same output
- **Tested**: All test cases pass on multiple backends
- **Documented**: This specification provides full reference

Core IL v1.0 is ready for production use.
