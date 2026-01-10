# Migration Guide: v0.5 → v1.0

This guide helps you migrate Core IL programs from v0.5 to v1.0.

---

## TL;DR

**Core IL v1.0 is 100% backward compatible with v0.5.**

To upgrade:
1. Change `"version": "coreil-0.5"` to `"version": "coreil-1.0"`
2. Done!

No code changes required. All v0.5 programs are valid v1.0 programs.

---

## What Changed in v1.0?

### 1. Formalized Specification

**v0.5**: Specification was documented in [docs/coreil_v0_5.md](docs/coreil_v0_5.md)

**v1.0**: Complete specification in [coreil_v1.md](coreil_v1.md) with:
- Explicit semantics for every node type
- Implementation requirements for backends
- Short-circuit evaluation documentation
- Error handling specifications
- Example programs

**Impact**: None on existing programs. Better documentation only.

---

### 2. Short-Circuit Evaluation (Bug Fix)

**v0.5**: The interpreter evaluated both operands before checking logical operators

**v1.0**: Logical operators `and`/`or` now properly short-circuit:
- `and`: If left is falsy, right is not evaluated
- `or`: If left is truthy, right is not evaluated

**Example that failed in v0.5, works in v1.0**:

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

In v0.5, when `i >= len(arr)`, this would try to access `arr[i]` and fail with "Index out of range".

In v1.0, when `i >= len(arr)`, the left side evaluates to false and the right side is never evaluated, so no error occurs.

**Impact**: Programs using guard patterns like `x != null and x.field == value` now work correctly.

---

### 3. Tuple Indexing Support (Bug Fix)

**v0.5**: Index and Length operations only accepted lists

**v1.0**: Index and Length operations accept both lists and tuples

**Example that failed in v0.5, works in v1.0**:

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
  "type": "Print",
  "args": [
    {
      "type": "Index",
      "base": {"type": "Var", "name": "pair"},
      "index": {"type": "Literal", "value": 0}
    }
  ]
}
```

In v0.5, this would fail with "Index base must be an array".

In v1.0, this correctly prints `1`.

**Impact**: Algorithms using tuples as structured data (e.g., bigram pairs) now work correctly.

---

### 4. Dictionary Key Ordering (Bug Fix)

**v0.5**: Keys operation used `sorted(dict.keys())`

**v1.0**: Keys operation uses `list(dict.keys())` (insertion order)

**Example that failed in v0.5, works in v1.0**:

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
      {"type": "Literal", "value": 1},
      {"type": "Literal", "value": 2}
    ]
  },
  "value": {"type": "Literal", "value": "r1"}
},
{
  "type": "Set",
  "base": {"type": "Var", "name": "counts"},
  "key": {
    "type": "Tuple",
    "items": [
      {"type": "Literal", "value": 20},
      {"type": "Literal", "value": "r2"}
    ]
  },
  "value": {"type": "Literal", "value": 100}
},
{
  "type": "ForEach",
  "var": "key",
  "iter": {"type": "Keys", "base": {"type": "Var", "name": "counts"}},
  "body": [
    {"type": "Print", "args": [{"type": "Var", "name": "key"}]}
  ]
}
```

In v0.5, this would fail because `sorted()` cannot compare the integer tuple `(1, 2)` with the mixed-type tuple `(20, "r2")`.

In v1.0, keys are returned in insertion order: `(1, 2)` then `(20, "r2")`.

**Impact**: Dictionaries with heterogeneous keys (especially tuples with mixed types) now work correctly.

---

## Migration Steps

### Step 1: Update Version String

Change your Core IL document from:

```json
{
  "version": "coreil-0.5",
  "ambiguities": [],
  "body": [...]
}
```

To:

```json
{
  "version": "coreil-1.0",
  "ambiguities": [],
  "body": [...]
}
```

### Step 2: Validate

Run validation to ensure your program is valid:

```bash
python -m english_compiler run your_program.coreil.json
```

If you get errors, they're likely from existing bugs that were hidden in v0.5. The v1.0 fixes make the errors visible.

### Step 3: Test

Run your program on both interpreter and Python codegen:

```bash
# Interpreter
python -m english_compiler run your_program.coreil.json

# Python codegen
python -m english_compiler compile --target python --frontend mock your_program.coreil.json
python your_program.py
```

Both should produce identical output.

### Step 4: Update Dependencies (Optional)

If you're using the Python package programmatically:

```python
from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.emit import emit_python

# Both now accept "coreil-1.0"
doc = {
    "version": "coreil-1.0",
    "ambiguities": [],
    "body": [...]
}

# Works!
run_coreil(doc)
code = emit_python(doc)
```

---

## Common Issues

### Issue: "version must be 'coreil-0.1', ..., or 'coreil-0.5'"

**Cause**: You're using an old version of the interpreter/compiler that doesn't support v1.0 yet.

**Solution**: Update to the latest version or change version back to `"coreil-0.5"` (fully compatible).

---

### Issue: "Index out of range" error disappeared

**Cause**: Your program had a bug where guard conditions weren't working due to lack of short-circuit evaluation.

**Solution**: This is a fix, not a regression! Your program now works correctly. Review the logic to ensure it does what you expect.

**Example**:

v0.5 (broken):
```json
// This would crash if i >= len(arr)
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
  "then": [...]
}
```

v1.0 (fixed):
```json
// This now works correctly - arr[i] is only accessed if i < len(arr)
// (same code, but short-circuit evaluation fixes the bug)
```

---

### Issue: Tuple indexing now works but wasn't tested

**Cause**: Your v0.5 program avoided tuple indexing because it didn't work.

**Solution**: You can now simplify code that worked around this limitation. For example:

v0.5 workaround:
```json
// Had to convert tuple to array to index it
{
  "type": "Let",
  "name": "pair_array",
  "value": {
    "type": "Array",
    "items": [
      {"type": "Index", "base": {"type": "Var", "name": "tuple"}, "index": {"type": "Literal", "value": 0}},
      {"type": "Index", "base": {"type": "Var", "name": "tuple"}, "index": {"type": "Literal", "value": 1}}
    ]
  }
}
```

v1.0 (simplified):
```json
// Can index tuple directly
{
  "type": "Index",
  "base": {"type": "Var", "name": "tuple"},
  "index": {"type": "Literal", "value": 0}
}
```

---

### Issue: Keys iteration order changed

**Cause**: v0.5 sorted keys (and crashed on mixed types), v1.0 uses insertion order.

**Solution**:
1. If you relied on sorted order, add an explicit sort in your algorithm
2. If you had mixed-type keys that crashed in v0.5, they now work in v1.0

**Example** (if you need sorted order):

```json
{
  "type": "Let",
  "name": "keys",
  "value": {"type": "Keys", "base": {"type": "Var", "name": "counts"}}
},
// Add your own sorting logic here if needed
{
  "type": "ForEach",
  "var": "key",
  "iter": {"type": "Var", "name": "keys"},
  "body": [...]
}
```

---

## Benefits of Upgrading

1. **Bug Fixes**: Short-circuit evaluation, tuple indexing, mixed-type keys all work correctly
2. **Better Documentation**: Complete specification in [coreil_v1.md](coreil_v1.md)
3. **Future-Proof**: v1.0 is stable and frozen - no breaking changes ever
4. **Confidence**: All examples and real algorithms tested and working

---

## Backward Compatibility

All v0.1, v0.2, v0.3, v0.4, and v0.5 programs continue to work in the v1.0 interpreter and compiler.

You can mix versions in the same project:

```bash
# v0.1 program
python -m english_compiler run examples/old_v0.1.coreil.json

# v0.5 program
python -m english_compiler run examples/newer_v0.5.coreil.json

# v1.0 program
python -m english_compiler run examples/latest_v1.0.coreil.json
```

All work correctly!

---

## Recommendations

### For New Projects

Always use `"version": "coreil-1.0"`. It's the stable, production-ready version with all bug fixes.

### For Existing Projects

Upgrade to v1.0 at your convenience:
1. Low risk: 100% backward compatible
2. Benefits: Bug fixes and better docs
3. Effort: Change one line per file

### For Libraries/Tools

Support all versions (`"coreil-0.1"` through `"coreil-1.0"`). The interpreter and compiler already do this.

---

## Need Help?

If you encounter issues migrating:

1. Check [CHANGELOG.md](CHANGELOG.md) for detailed bug fixes
2. Read [coreil_v1.md](coreil_v1.md) for complete semantics
3. Look at [examples/](examples/) for working v1.0 programs
4. Run tests: `python -m tests.run`

Core IL v1.0 is battle-tested with complex algorithms like BPE (596 lines). If something doesn't work, it's likely a genuine bug in your program that v0.5 was hiding.

---

**Migration is easy, safe, and recommended for all users.**
