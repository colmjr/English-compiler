# Core IL v0.1 (JSON)

This is a minimal JSON-based intermediate language for simple programs.

## Top-level

A Core IL document is a JSON object with:

- `version`: string, must be `"coreil-0.1"`.
- `ambiguities`: optional array, default empty. Reserved for future ambiguity markers.
- `body`: array of statement objects.

Example top-level shape:

```json
{
  "version": "coreil-0.1",
  "ambiguities": [],
  "body": []
}
```

## Statements

Each statement is an object with a `"type"` field.

### Let
Declare a new variable.

```json
{ "type": "Let", "name": "x", "value": <Expr> }
```

### Assign
Reassign an existing variable.

```json
{ "type": "Assign", "name": "x", "value": <Expr> }
```

### If
Conditional branch.

```json
{
  "type": "If",
  "test": <Expr>,
  "then": [ <Stmt> ],
  "else": [ <Stmt> ]
}
```

- `else` is optional; if omitted, treat as empty array.

### While
Loop.

```json
{
  "type": "While",
  "test": <Expr>,
  "body": [ <Stmt> ]
}
```

### Call (statement form)
Invoke a builtin; result is ignored.

```json
{ "type": "Call", "name": "print", "args": [ <Expr> ] }
```

## Expressions

Expressions are objects with a `"type"` field.

### Literal

```json
{ "type": "Literal", "value": 123 }
{ "type": "Literal", "value": "hello" }
{ "type": "Literal", "value": true }
```

### Var
Read a variable.

```json
{ "type": "Var", "name": "x" }
```

### Binary
Binary operators:
`+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `and`, `or`

```json
{ "type": "Binary", "op": "+", "left": <Expr>, "right": <Expr> }
```

### Call (expression form)
Invoke a builtin and use its return value.

```json
{ "type": "Call", "name": "some_builtin", "args": [ <Expr> ] }
```

## Builtins (v0.1)

- `print`: prints its arguments. Return value is implementation-defined (may be `null`).

## Notes

- Statement arrays execute in order.
- Variables are in a single global scope.
- Implementations should error on unknown statement/expression types or operators.
