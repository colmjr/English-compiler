# Core IL v0.4 (JSON)

Core IL v0.4 extends v0.3 with minimal map/record support. All v0.1, v0.2, and v0.3 programs remain valid.

## Top-level

A Core IL document is a JSON object with:

- `version`: string, `"coreil-0.1"`, `"coreil-0.2"`, `"coreil-0.3"`, or `"coreil-0.4"`.
- `ambiguities`: optional array, default empty.
- `body`: array of statement objects.

Example:

```json
{
  "version": "coreil-0.4",
  "ambiguities": [],
  "body": []
}
```

## Map/Record support (v0.4)

### Map expression

Create a map (dictionary/record) with key-value pairs:

```json
{
  "type": "Map",
  "items": [
    {
      "key": <expr>,
      "value": <expr>
    },
    ...
  ]
}
```

- `items` is an array of key-value pair objects.
- Each item must have `key` and `value` fields, both expressions.
- Keys must evaluate to strings or integers.
- Values can be any type.

Example:

```json
{
  "type": "Map",
  "items": [
    {
      "key": {"type": "Literal", "value": "a"},
      "value": {"type": "Literal", "value": 1}
    },
    {
      "key": {"type": "Literal", "value": "b"},
      "value": {"type": "Literal", "value": 2}
    }
  ]
}
```

### Get expression

Retrieve a value from a map by key:

```json
{
  "type": "Get",
  "base": <expr>,
  "key": <expr>
}
```

- `base` must evaluate to a map.
- `key` must evaluate to a string or integer.
- Returns the value associated with the key.
- **Returns `null` (Python `None`) if the key is not found.**

Example:

```json
{
  "type": "Get",
  "base": {"type": "Var", "name": "myMap"},
  "key": {"type": "Literal", "value": "someKey"}
}
```

### Set statement

Set a key-value pair in a map:

```json
{
  "type": "Set",
  "base": <expr>,
  "key": <expr>,
  "value": <expr>
}
```

- `base` must evaluate to a map.
- `key` must evaluate to a string or integer.
- `value` can be any type.
- If the key already exists, its value is updated.
- If the key doesn't exist, it's added to the map.

Example:

```json
{
  "type": "Set",
  "base": {"type": "Var", "name": "myMap"},
  "key": {"type": "Literal", "value": "newKey"},
  "value": {"type": "Literal", "value": 42}
}
```

## Complete example

```json
{
  "version": "coreil-0.4",
  "body": [
    {
      "type": "Let",
      "name": "config",
      "value": {
        "type": "Map",
        "items": [
          {
            "key": {"type": "Literal", "value": "host"},
            "value": {"type": "Literal", "value": "localhost"}
          },
          {
            "key": {"type": "Literal", "value": "port"},
            "value": {"type": "Literal", "value": 8080}
          }
        ]
      }
    },
    {
      "type": "Set",
      "base": {"type": "Var", "name": "config"},
      "key": {"type": "Literal", "value": "timeout"},
      "value": {"type": "Literal", "value": 30}
    },
    {
      "type": "Print",
      "args": [
        {
          "type": "Get",
          "base": {"type": "Var", "name": "config"},
          "key": {"type": "Literal", "value": "port"}
        }
      ]
    }
  ]
}
```

This program:
1. Creates a map with `host` and `port` keys
2. Adds a `timeout` key to the map
3. Prints the value of `port` (outputs: `8080`)

## Design notes

- Maps are implemented as Python dictionaries.
- Keys can be strings or integers (enforced at runtime).
- Get returns `null` (Python `None`) for missing keys, not an error.
- Maps are mutable and passed by reference (like arrays).
- All previous Core IL versions (0.1-0.3) remain fully compatible.
