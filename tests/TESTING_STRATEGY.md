# Testing Strategy for English Compiler

## Overview

The English compiler has a comprehensive testing strategy that ensures correctness, stability, and backend parity across all components.

## Test Suites

### 1. Basic Example Tests (`tests/run.py`)

**Purpose**: Verify Core IL primitives work correctly in the interpreter.

**Run Command**:
```bash
python -m tests.run
```

**Coverage**:
- Individual Core IL node types (Print, Binary, Array, Index, etc.)
- Basic control flow (If, While, For, ForEach)
- Functions (FuncDef, Call, Return)
- Collections (Array, Map, Tuple)

**Test Files**: Examples in `examples/` directory
- `hello.coreil.json` - Basic Print
- `math.coreil.json` - Binary arithmetic
- `if.coreil.json` - Conditional logic
- `array_*.coreil.json` - Array operations
- `bubble_sort.coreil.json` - Nested loops and swaps
- `fn_add.coreil.json` - Function calls
- `for_sum.coreil.json` - For loops
- `foreach_print.coreil.json` - ForEach loops
- `map_demo.coreil.json` - Dictionary operations

**What It Tests**:
- Core IL interpreter correctness
- Validation rules
- Expected output matching

**What It Doesn't Test**:
- Python backend (no codegen)
- Backend parity
- End-to-end pipeline (English → Core IL)

### 2. Algorithm Regression Tests (`tests/run_algorithms.py`)

**Purpose**: Enforce strict guarantees across the entire compiler pipeline.

**Run Command**:
```bash
python -m tests.run_algorithms
```

**Coverage**: 8 canonical algorithms in natural English
- `sum.txt` - Array accumulation
- `count_occurrences.txt` - Dictionary operations
- `reverse_array.txt` - Array construction with loops
- `max_element.txt` - Finding extremum values
- `bubble_sort.txt` - Nested loops and swaps
- `linear_search.txt` - Early loop termination
- `bigram_frequency.txt` - Tuples as dictionary keys
- `mean.txt` - Function definition and calls

**What It Tests**:
1. **English → Core IL generation** (via frontend)
2. **Core IL validation** (structural and semantic)
3. **Invalid call detection** (disallowed helper functions)
4. **Interpreter execution** (Core IL semantics)
5. **Python code generation** (Core IL → Python transpilation)
6. **Python execution** (generated code runs correctly)
7. **Backend parity** (interpreter output == Python output)

**Failure Modes Detected**:
- Validation failures (malformed Core IL)
- Invalid helper calls (`get_or_default`, `append`, etc.)
- Interpreter errors (runtime errors, crashes)
- Python codegen failures (transpilation errors)
- Python execution failures (generated code crashes)
- Backend parity failures (semantic divergence)

**Key Properties**:
- Zero external dependencies (stdlib only)
- Deterministic (same input → same output)
- Fast (uses mock frontend by default)
- Isolated (Python runs in subprocess)
- Timeout protected (10-second limit)

### 3. Specialized Tests

#### Short-Circuit Evaluation (`tests/test_short_circuit.py`)
Tests the critical short-circuit semantics for `and`/`or` operators that prevent runtime errors.

```bash
python -m tests.test_short_circuit
```

#### Lowering Pass (`tests/test_lower.py`)
Tests the transformation of syntax sugar (For/ForEach) into While loops.

```bash
python -m tests.test_lower
```

#### Regression Suite Tests (`tests/test_regression_suite.py`)
Meta-tests that verify the regression suite itself correctly detects failures.

```bash
python -m tests.test_regression_suite
```

## Testing Philosophy

### 1. Determinism First
All tests are deterministic. The only non-deterministic component (LLM frontend) is mocked by default.

### 2. Backend Parity is Critical
The interpreter is the reference implementation. The Python backend must produce **identical** output for all programs. Any divergence is a bug.

### 3. Closed Specification Enforcement
Core IL v1.0 is sealed. Tests explicitly check that no disallowed helper functions are used. All operations must use explicit primitives.

### 4. Real-World Algorithms
The golden corpus uses realistic algorithms that real users would write, not compiler-aware test cases.

### 5. Fast Feedback
Basic tests run in <1 second. Algorithm tests complete in ~2 seconds. This enables fast iteration during development.

## CI/CD Integration

### Pre-Commit Checks
```bash
# Run all tests before committing
python -m tests.run && \
python -m tests.run_algorithms && \
python -m tests.test_short_circuit
```

### Release Checklist
Before releasing a new version:
1. All basic tests pass (`tests.run`)
2. All algorithm regression tests pass (`tests.run_algorithms`)
3. Short-circuit tests pass (`tests.test_short_circuit`)
4. Lowering tests pass (`tests.test_lower`)
5. Regression suite meta-tests pass (`tests.test_regression_suite`)

## Adding New Tests

### Adding to Basic Tests
Edit `tests/run.py`:
```python
_run_example(examples / "new_test.coreil.json", "expected output\n")
```

### Adding to Algorithm Corpus
1. Create `tests/algorithms/new_algorithm.txt` with natural English pseudocode
2. Define input clearly
3. Describe algorithm in simple steps
4. No need to modify `run_algorithms.py` (auto-discovers `.txt` files)

Example structure:
```
Describe what the algorithm does.

Input: [example, data, here]

Step 1: ...
Step 2: ...
Step N: Print the result.
```

### Adding Specialized Tests
Create a new test file in `tests/` directory and add to CI checks.

## Test Output Examples

### Success (Basic Tests)
```
All tests passed.
```

### Success (Algorithm Tests)
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

### Failure (Backend Parity)
```
Running 8 algorithm regression tests...

Testing sum... ✗

======================================================================
FAILURES:
======================================================================

1. sum: Output mismatch!
Interpreter output:
43

Python output:
42

1/8 tests failed
```

### Failure (Invalid Helper Call)
```
Testing count_occurrences... ✗

======================================================================
FAILURES:
======================================================================

1. count_occurrences: Invalid helper call 'get_or_default' found.
Use explicit primitives instead (GetDefault, Keys, Push).
```

## Test Coverage Summary

| Component | Basic Tests | Algorithm Tests | Specialized Tests |
|-----------|-------------|-----------------|-------------------|
| **Interpreter** | ✓ | ✓ | ✓ |
| **Python Backend** | ✗ | ✓ | ✗ |
| **Validation** | ✓ | ✓ | ✓ |
| **Frontend** | ✗ | ✓ (mock) | ✗ |
| **Lowering** | ✗ | ✗ | ✓ |
| **Backend Parity** | ✗ | ✓ | ✗ |
| **Invalid Calls** | ✗ | ✓ | ✗ |
| **Short-Circuit** | ✗ | ✗ | ✓ |

## Future Enhancements

Possible additions to the test suite:
1. **Golden outputs**: Store expected algorithm outputs for extra verification
2. **Performance tests**: Track execution time and memory usage
3. **Fuzzing**: Generate random valid Core IL and check parity
4. **Coverage tracking**: Measure which Core IL nodes are exercised
5. **Claude frontend tests**: Test real LLM generation (requires API key)
6. **Error message tests**: Verify error messages are clear and helpful
7. **Edge case tests**: Boundary conditions, empty collections, etc.
