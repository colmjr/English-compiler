# Algorithm Corpus Regression Tests

## Overview

The algorithm corpus regression test suite enforces strict guarantees across the Core IL interpreter and Python backend.

**Test Location**: `tests/run_algorithms.py`

**Run Command**:
```bash
python -m tests.run_algorithms
```

## What It Tests

For each `.txt` file in `tests/algorithms/`:

1. **English → Core IL Generation**: Uses frontend to generate Core IL JSON
2. **Validation**: Ensures Core IL passes all structural and semantic validation
3. **Invalid Call Detection**: Ensures no disallowed helper functions are used
4. **Interpreter Execution**: Runs Core IL via interpreter and captures stdout
5. **Python Code Generation**: Transpiles Core IL to Python
6. **Python Execution**: Runs generated Python in subprocess and captures stdout
7. **Backend Parity**: Compares interpreter output vs Python output (must match exactly)

## Failure Modes Caught

### 1. Validation Failures
**What**: Core IL JSON is malformed or semantically invalid
**Example**: Missing required fields, invalid node types, type mismatches
**Output**:
```
Testing sum... ✗

FAILURES:
sum: Validation failed:
body[0].type: Unknown statement type 'InvalidNode'
```

### 2. Invalid Helper Calls
**What**: Disallowed helper functions like `get_or_default`, `append`, `keys`, `entries`
**Why**: Core IL v1.0 is sealed - must use explicit primitives (GetDefault, Push, Keys)
**Example**: Using `Call("append", [...])` instead of `Push` statement
**Output**:
```
Testing count_occurrences... ✗

FAILURES:
count_occurrences: Invalid helper call 'get_or_default' found.
Use explicit primitives instead (GetDefault, Keys, Push).
```

### 3. Interpreter Errors
**What**: Interpreter raises exception or exits with non-zero code
**Example**: Runtime type error, division by zero, recursion limit exceeded
**Output**:
```
Testing bubble_sort... ✗

FAILURES:
bubble_sort: Interpreter error: runtime error: index out of bounds: 10 >= 5
```

### 4. Python Codegen Failures
**What**: Core IL cannot be transpiled to Python
**Example**: Unhandled node type, invalid Python syntax generation
**Output**:
```
Testing mean... ✗

FAILURES:
mean: Python codegen failed: Unknown expression type: InvalidExpr
```

### 5. Python Execution Failures
**What**: Generated Python code crashes or exits non-zero
**Example**: SyntaxError, NameError, runtime exception
**Output**:
```
Testing linear_search... ✗

FAILURES:
linear_search: Python execution failed with exit code 1
stderr: NameError: name 'undefined_var' is not defined
```

### 6. Backend Parity Failures (Most Critical)
**What**: Interpreter output ≠ Python output
**Why**: This indicates semantic divergence between backends
**Example**: Different short-circuit behavior, different dictionary ordering
**Output**:
```
Testing bigram_frequency... ✗

FAILURES:
bigram_frequency: Output mismatch!
Interpreter output:
{(1, 2): 2, (2, 1): 1, (2, 3): 1, (3, 2): 1}

Python output:
{(1, 2): 2, (2, 1): 1, (3, 2): 1, (2, 3): 1}
```

## Current Test Coverage

The golden corpus includes 8 algorithms that collectively stress all major Core IL constructs:

| Algorithm | Core IL Features Tested |
|-----------|------------------------|
| **sum** | ForEach loops, variable accumulation, Print |
| **count_occurrences** | Dictionary operations, GetDefault, conditional updates |
| **reverse_array** | While loops, Push, descending index arithmetic |
| **max_element** | Array indexing, comparison operators, extremum pattern |
| **bubble_sort** | Nested For loops, SetIndex, swap pattern |
| **linear_search** | For with early termination, equality testing, sentinel values |
| **bigram_frequency** | Tuple construction, tuples as dict keys, range bounds |
| **mean** | FuncDef, Call, Return, division |

## Integration with CI/CD

This test suite should be run:
- **On every commit** to catch regressions early
- **Before releases** to ensure production readiness
- **After Core IL changes** to verify backward compatibility
- **After backend changes** to verify parity

Example CI command:
```bash
# Run all tests
python -m tests.run && python -m tests.run_algorithms
```

## Success Output

When all tests pass:
```
Running 8 algorithm regression tests...

Testing bigram_frequency... ✓
Testing bubble_sort... ✓
Testing count_occurrences... ✓
Testing linear_search... ✓
Testing max_element... ✓
Testing mean... ✓
Testing reverse_array... ✓
Testing sum... ✓

All 8 algorithm regression tests passed! ✓

Verified:
  • Core IL validation passes
  • Interpreter executes successfully
  • Python backend executes successfully
  • Backend parity (interpreter output == Python output)
  • No invalid helper calls
```

## Implementation Details

- **Zero external dependencies**: Uses only stdlib (`subprocess`, `tempfile`)
- **Deterministic**: Same input always produces same result
- **Fast**: Uses mock frontend by default (no LLM calls)
- **Isolated**: Python execution happens in subprocess (can't affect test process)
- **Timeout protected**: Python execution has 10-second timeout

## Future Enhancements

Possible additions:
1. **Golden outputs**: Store expected outputs and compare against them
2. **Performance testing**: Measure and track execution time
3. **Memory profiling**: Detect memory leaks or excessive allocation
4. **Fuzzing**: Generate random valid Core IL and check parity
5. **Coverage**: Track which Core IL nodes are exercised by corpus
