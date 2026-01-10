# Changelog

## Core IL v1.0 - 2026-01-10

**Status: Stable and Production Ready**

This release marks the first stable, production-ready version of Core IL. The specification is now frozen and all existing tests pass with 100% parity between interpreter and Python code generation.

### Major Changes

- **Formalized Specification**: Created comprehensive [coreil_v1.md](coreil_v1.md) documenting all node types, semantics, and invariants
- **Short-Circuit Evaluation**: Implemented proper short-circuit evaluation for `and` and `or` operators (critical bug fix)
- **Tuple Support**: Enhanced interpreter and codegen to support tuple indexing and length operations
- **Dictionary Keys**: Fixed Keys operation to use insertion order instead of sorted order (supports mixed-type keys)
- **Version Support**: All components now accept `"coreil-1.0"` as a valid version string

### Breaking Changes

None. Core IL v1.0 is fully backward compatible with v0.5. Programs written in v0.5 work in v1.0 without modification.

### Bug Fixes

1. **Short-Circuit Evaluation** ([english_compiler/coreil/interp.py:67-112](english_compiler/coreil/interp.py#L67-L112))
   - **Problem**: The interpreter evaluated both operands of `and`/`or` operators before checking the operator, causing runtime errors when the right side accessed out-of-bounds indices
   - **Solution**: Implemented proper short-circuit evaluation - `and` returns false without evaluating right side when left is falsy, `or` returns true without evaluating right side when left is truthy
   - **Impact**: Enables safe guard patterns like `i < len(arr) and arr[i] == value`

2. **Tuple Indexing** ([english_compiler/coreil/interp.py:120-130](english_compiler/coreil/interp.py#L120-L130))
   - **Problem**: Index and Length operations only accepted lists, rejecting tuples
   - **Solution**: Updated type checks to accept both `list` and `tuple` (both are Python sequences)
   - **Impact**: Tuples can now be indexed and measured, essential for algorithms using tuples as structured data

3. **Mixed-Type Dictionary Keys** ([english_compiler/coreil/emit.py:139-143](english_compiler/coreil/emit.py#L139-L143))
   - **Problem**: Keys operation used `sorted()` which fails on mixed-type keys like `(20, 10)` and `(1, "r1")`
   - **Solution**: Changed from `sorted(dict.keys())` to `list(dict.keys())` to preserve insertion order
   - **Impact**: Dictionaries with heterogeneous tuple keys now work correctly (e.g., BPE algorithm)

### Testing

All test suites pass:
- `python -m tests.run` - Core interpreter and validation tests
- `python -m tests.test_short_circuit` - Short-circuit evaluation tests
- `python -m tests.run_parity` - Interpreter vs codegen parity tests

Successfully tested with real-world algorithms:
- Array operations (sum, reverse, max, bubble sort)
- String processing (bigram frequency)
- Advanced algorithms (Byte Pair Encoding with 596-line Core IL)

### Documentation

- **[coreil_v1.md](coreil_v1.md)**: Complete specification with philosophy, all node types, semantics, examples, and implementation requirements
- **[README.md](README.md)**: Updated to reflect v1.0 status and architecture
- **Historical docs**: Preserved in `docs/` directory for reference

### Future Work

Core IL v1.0 is feature-complete and frozen. Potential future versions might add:
- Type annotations (v2.0)
- Module system (v2.0)
- String operations (v1.1)
- List slicing (v1.1)
- Exception handling (v2.0)

However, v1.0 remains stable for production use indefinitely.

---

## Core IL v0.5 - 2025-12-XX

**Sealed Primitives Release**

### Features

- Added explicit primitives: GetDefault, Keys, Push, Tuple
- Restricted Call nodes to user-defined functions only
- Disallowed helper function calls (`get_or_default`, `keys`, `append`, `entries`)
- Made Core IL a closed specification

### Purpose

This release "sealed" the IR to prevent LLMs from inventing helper functions, ensuring all operations use explicit primitives that backends can understand and optimize.

---

## Core IL v0.3 - 2025-11-XX

**Functions and Control Flow**

### Features

- Added FuncDef for function definitions
- Added Return statements
- Added For loops with Range iterators
- Added ForEach loops for collection iteration

---

## Core IL v0.2 - 2025-11-XX

**Arrays and Data Structures**

### Features

- Added Array type
- Added Index operation for array access
- Added SetIndex for array mutation
- Added Length operation

---

## Core IL v0.1 - 2025-10-XX

**Initial Release**

### Features

- Basic statements: Let, Assign, If, While, Print
- Basic expressions: Literal, Var, Binary
- Map (dictionary) type with Get and Set operations
- Binary operators: arithmetic, comparison, logical
- Validation and interpreter
