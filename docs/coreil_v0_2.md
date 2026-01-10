# Core IL v0.2 (JSON)

Core IL v0.2 extends v0.1 with arrays and indexing. All v0.1 programs remain valid.

## Top-level

A Core IL document is a JSON object with:

- `version`: string, `"coreil-0.1"` or `"coreil-0.2"`.
- `ambiguities`: optional array, default empty.
- `body`: array of statement objects.

Example:

```json
{
  "version": "coreil-0.2",
  "ambiguities": [],
  "body": []
}
```

## New expressions (v0.2)

### Array

```json
{ "type": "Array", "items": [ <Expr>, ... ] }
```

### Index

```json
{ "type": "Index", "base": <Expr>, "index": <Expr> }
```

### Length

```json
{ "type": "Length", "base": <Expr> }
```

## New statements (v0.2)

### SetIndex

```json
{ "type": "SetIndex", "base": <Expr>, "index": <Expr>, "value": <Expr> }
```

## Notes

- v0.2 adds structural support for arrays and indexing.
- Semantics are defined by the interpreter; this version may validate structure only.
