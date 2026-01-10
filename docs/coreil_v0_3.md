# Core IL v0.3 (JSON)

Core IL v0.3 extends v0.2 with function definitions, returns, and optional syntax sugar for ranges and for-loops. All v0.1 and v0.2 programs remain valid.

## Top-level

A Core IL document is a JSON object with:

- `version`: string, `"coreil-0.1"`, `"coreil-0.2"`, or `"coreil-0.3"`.
- `ambiguities`: optional array, default empty.
- `body`: array of statement objects.

Example:

```json
{
  "version": "coreil-0.3",
  "ambiguities": [],
  "body": []
}
```

## Function statements (v0.3)

### FuncDef

```json
{ "type": "FuncDef", "name": "fname", "params": ["a", "b"], "body": [ <Stmt> ] }
```

### Return

```json
{ "type": "Return", "value": <Expr> }
```

- `value` is optional. If omitted, the return value is `null`.
- `Return` is only valid inside a `FuncDef` body.

## Call expression

Call is an expression that invokes a function by name:

```json
{ "type": "Call", "name": "fname", "args": [ <Expr>, ... ] }
```

## Range and For (syntax sugar)

### Range expression

```json
{ "type": "Range", "from": <Expr>, "to": <Expr>, "inclusive": false }
```

- `inclusive` is optional; default is `false`.
- Default semantics: `[from, to)`.

### For statement

```json
{ "type": "For", "var": "i", "iter": <Expr>, "body": [ <Stmt> ] }
```

Lowering rule (when `iter` is `Range`):

```text
Let i = from
While i < to:
  body
  i = i + 1
```

If `inclusive` is `true`, the comparison uses `<=`.

## Notes

- v0.3 adds structural support for functions and for/range syntax sugar.
- The interpreter runs lowered Core IL; syntax sugar is not executed directly.
