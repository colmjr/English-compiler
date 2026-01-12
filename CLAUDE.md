# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The English Compiler translates English pseudocode into executable code through a deterministic intermediate representation (Core IL). The system uses a three-stage pipeline:

```
English Text → LLM Frontend → Core IL (JSON) → Deterministic Backends
```

**Key principle**: Only the LLM frontend is non-deterministic. Core IL and all backends are completely deterministic and must produce identical output.

## Commands

### Testing

```bash
# Run basic example tests (Core IL primitives and interpreter)
python -m tests.run

# Run algorithm regression tests (full pipeline with backend parity)
python -m tests.run_algorithms

# Run specialized tests
python -m tests.test_short_circuit    # Short-circuit evaluation
python -m tests.test_lower            # Lowering pass (For/ForEach to While)
python -m tests.test_regression_suite # Meta-tests for regression suite
```

### Compilation and Execution

```bash
# Compile with mock frontend (default when no API key)
python -m english_compiler compile examples/hello.txt

# Compile with Claude frontend
python -m english_compiler compile --frontend claude examples/hello.txt

# Generate Python code (in addition to Core IL)
python -m english_compiler compile --target python examples/hello.txt

# Force regeneration (bypass cache)
python -m english_compiler compile --regen examples/hello.txt

# Fail if regeneration required (CI mode)
python -m english_compiler compile --freeze examples/hello.txt

# Run an existing Core IL file directly
python -m english_compiler run examples/hello.coreil.json
```

### Claude Demo

```bash
# Test Claude API integration (prints generated Core IL)
python -m scripts.demo_claude_compile
```

## Architecture

### Directory Structure

- `english_compiler/` - Main package
  - `coreil/` - Core IL implementation
    - `validate.py` - Core IL validation (structural and semantic)
    - `interp.py` - Reference interpreter (deterministic execution)
    - `emit.py` - Python code generator (transpilation)
    - `lower.py` - Lowering pass (For/ForEach → While)
  - `frontend/` - LLM frontends
    - `claude.py` - Claude API integration
    - `mock_llm.py` - Mock generator (deterministic, for testing)
    - `prompt.txt` - System prompt for Core IL generation
    - `coreil_schema.py` - JSON schema for Core IL v1.1
  - `__main__.py` - CLI entry point

- `tests/` - Test suite
  - `run.py` - Basic example tests
  - `run_algorithms.py` - Algorithm regression tests
  - `algorithms/` - Natural English algorithm corpus
  - `test_short_circuit.py` - Short-circuit evaluation tests
  - `test_lower.py` - Lowering pass tests
  - `test_regression_suite.py` - Meta-tests

- `examples/` - Example Core IL programs and source files
- `docs/` - Historical Core IL specifications (v0.1-v0.5)

### Core IL Version Policy

**Current stable version**: Core IL v1.1 (`"coreil-1.1"`)

Core IL v1.0 is frozen and stable. Core IL v1.1 adds Record, Set (data structure), and string operations while maintaining full backward compatibility.

All versions from v0.1 through v1.1 are supported for backward compatibility. The codebase uses version constants:

```python
from english_compiler.coreil import COREIL_VERSION, SUPPORTED_VERSIONS
```

### Pipeline Stages

1. **Frontend (Non-deterministic)**
   - Translates English/pseudocode → Core IL JSON
   - Mock frontend: deterministic (for testing)
   - Claude frontend: uses Anthropic API
   - Output is cached with source hash in `.lock.json` files

2. **Core IL (Deterministic)**
   - Closed specification - all operations explicitly defined
   - No extension mechanism or helper functions allowed
   - Validated by `validate.py` before execution
   - Lowering pass transforms For/ForEach into While loops

3. **Backends (Deterministic)**
   - Interpreter: direct execution of Core IL
   - Python codegen: transpiles to executable Python
   - Both backends must produce identical output (verified by tests)

### Artifacts

When compiling `foo.txt`, three files are generated:
- `foo.coreil.json` - Core IL program (always)
- `foo.lock.json` - cache metadata (source hash, Core IL hash, model, timestamp)
- `foo.py` - executable Python code (only with `--target python`)

Cache reuse is based on matching source hash and Core IL hash.

## Core IL Fundamentals

### Node Categories

**Expressions** (evaluate to values):
- Literal, Var, Binary, Array, Tuple, Map, Record, Set
- Index, Length, Get, GetDefault, Keys, GetField, SetHas, SetSize
- StringLength, Substring, CharAt, Join
- Range, Call

**Statements** (perform actions):
- Let, Assign, SetIndex, Set, Push, SetField, SetAdd, SetRemove
- Print, If, While, For, ForEach
- FuncDef, Return

### Critical Rules

1. **No Helper Functions**: Core IL is sealed. Do not invent helpers like `get_or_default`, `append`, `keys`, `contains`. Use explicit primitives (GetDefault, Push, Keys, SetHas).

2. **Backend Parity**: Interpreter and Python backend must produce identical output. Any divergence is a bug. The algorithm regression tests enforce this.

3. **Short-Circuit Evaluation**: Logical operators (`and`, `or`) must implement proper short-circuiting to prevent runtime errors.

4. **Lowering Pass**: For and ForEach loops are syntax sugar. The lowering pass (`lower.py`) transforms them to While loops before backend execution.

5. **Version Markers**: All core modules (`validate.py`, `interp.py`, `emit.py`) include explicit version markers in docstrings and constants.

### Common Primitives

**Dictionary operations**:
```json
{"type": "GetDefault", "base": <map>, "key": <key>, "default": <value>}
{"type": "Keys", "base": <map>}
{"type": "Set", "base": <map>, "key": <key>, "value": <value>}
```

**Array operations**:
```json
{"type": "Push", "base": <array>, "value": <value>}
{"type": "Index", "base": <array>, "index": <expr>}
{"type": "Length", "base": <array>}
```

**Tuple (immutable, hashable)**:
```json
{"type": "Tuple", "items": [<expr>, ...]}
```

**Record (mutable named fields - v1.1)**:
```json
{"type": "Record", "fields": {"x": <expr>, "y": <expr>}}
{"type": "GetField", "base": <record>, "field": "x"}
{"type": "SetField", "base": <record>, "field": "x", "value": <expr>}
```

**Set (data structure - v1.1)**:
```json
{"type": "Set", "items": [<expr>, ...]}
{"type": "SetHas", "base": <set>, "item": <expr>}
{"type": "SetAdd", "base": <set>, "item": <expr>}
```

**Loops**:
```json
{"type": "For", "var": "i", "iter": {"type": "Range", "from": 0, "to": 10, "inclusive": false}, "body": [...]}
{"type": "ForEach", "var": "x", "iter": <array_expr>, "body": [...]}
```

## Testing Strategy

### Test Hierarchy

1. **Basic Tests** (`tests.run`)
   - Tests individual Core IL primitives
   - Interpreter correctness only
   - Fast feedback (~1 second)

2. **Algorithm Regression Tests** (`tests.run_algorithms`)
   - Full pipeline validation
   - Backend parity enforcement (interpreter == Python)
   - Invalid helper call detection
   - Golden corpus of 8+ realistic algorithms
   - Slower but comprehensive (~2 seconds)

3. **Specialized Tests**
   - Short-circuit evaluation
   - Lowering pass correctness
   - Regression suite meta-tests

### Backend Parity Requirements

The interpreter is the reference implementation. When modifying the Python backend (`emit.py`):

1. All algorithm regression tests must pass
2. Interpreter output must exactly match Python output
3. Both backends must handle the same Core IL constructs
4. Error messages should be consistent

### Adding Tests

**Basic test**:
Edit `tests/run.py` and add:
```python
_run_example(examples / "new_test.coreil.json", "expected output\n")
```

**Algorithm test**:
Create `tests/algorithms/new_algorithm.txt` with natural English pseudocode. The test runner auto-discovers `.txt` files.

## Common Pitfalls

1. **Don't bypass validation**: Always call `validate_coreil()` before executing Core IL.

2. **Don't mix node categories**: Expressions cannot contain statements. Use proper nesting.

3. **Don't assume static types**: Core IL uses runtime type checking. Operations validate inputs and produce clear error messages.

4. **Don't modify v1.0 semantics**: v1.0 is frozen. New features go in v1.1+ with backward compatibility.

5. **Don't skip lowering**: For/ForEach must be lowered before backend execution (happens automatically in `emit_python()`).

6. **Don't invent helper functions**: When LLM generates Core IL, it must use explicit primitives only. Check `english_compiler/frontend/prompt.txt` for the system prompt that enforces this.

## Exit Codes

- `0` - Success
- `1` - Error (I/O, validation failure, runtime error)
- `2` - Ambiguities present (artifacts still written, but user should review)

## Environment Variables

```bash
# Claude API configuration
export ANTHROPIC_API_KEY="your_api_key"
export ANTHROPIC_MODEL="claude-sonnet-4-5"  # or other model
export ANTHROPIC_MAX_TOKENS="4096"
```

## Key Documentation

- `coreil_v1.md` - Complete Core IL v1.0 specification
- `STATUS.md` - Project status and capabilities
- `VERSIONING.md` - Version strategy and code hygiene
- `MIGRATION.md` - Upgrade guide from v0.5 to v1.0
- `QUICK_REFERENCE.md` - Fast syntax reference
- `tests/TESTING_STRATEGY.md` - Detailed testing documentation
- `tests/ALGORITHM_TESTS.md` - Algorithm corpus details