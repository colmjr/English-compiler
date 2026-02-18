# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

This is a Python project. Use the virtual environment at `.venv/`. If pip or imports fail, check for alternate Python installations before retrying repeatedly.

## Project Philosophy

When implementing features for english-compiler, respect the project's philosophy: this is an English/natural-language compiler. Prefer LLM-powered approaches over hardcoded logic where the project philosophy calls for it.

## Git Workflow

Always create PRs instead of pushing directly to main. This repo uses branch protection — never attempt `git push origin main` directly.

When resolving merge conflicts, carefully audit ALL features from both branches. Do not silently drop functionality (e.g., unary Not support, increment steps in For loops).

## Documentation

After implementing any feature, always update relevant documentation before committing. Check README.md, docs/, and CLI --help text for anything that needs updating.

## File Editing Rules

When creating new analysis or output files, always create them as separate files — never modify the original source data files unless explicitly asked.

## Project Overview

The English Compiler translates English pseudocode into executable code through a deterministic intermediate representation (Core IL). The system uses a three-stage pipeline:

```
English Text → LLM Frontend → Core IL (JSON) → Deterministic Backends
```

**Key principle**: Only the LLM frontend is non-deterministic. Core IL and all backends are completely deterministic and must produce identical output.

## Commands

### Testing

```bash
# Core test suites (run these first)
python -m tests.run                    # Core IL primitives and interpreter
python -m tests.run_algorithms         # Algorithm regression (backend parity)
python -m tests.run_parity             # Backend parity checks

# Specialized tests
python -m tests.test_break_continue    # Break/Continue loop control
python -m tests.test_debug             # Interactive debugger
python -m tests.test_deque             # Deque operations
python -m tests.test_explain           # Reverse compiler (Core IL → English)
python -m tests.test_explain_errors    # LLM error explanations
python -m tests.test_go               # Go backend codegen + parity
python -m tests.test_helpers           # Helper utilities
python -m tests.test_javascript        # JavaScript backend codegen
python -m tests.test_lint              # Static analysis (linter) rules
python -m tests.test_lower             # Lowering pass (For/ForEach to While)
python -m tests.test_map               # Map/dictionary operations
python -m tests.test_optimize          # Core IL optimizer
python -m tests.test_record            # Record operations
python -m tests.test_regression_suite  # Meta-tests for regression suite
python -m tests.test_rust              # Rust backend codegen + parity
python -m tests.test_set_ops           # Set operations
python -m tests.test_settings          # Config/settings
python -m tests.test_short_circuit     # Short-circuit evaluation
python -m tests.test_slice             # Slice expression behavior
python -m tests.test_source_map        # Source map (English→CoreIL→target)
python -m tests.test_string_ops        # String operations
python -m tests.test_switch            # Switch statement pattern matching
python -m tests.test_try_catch         # Exception handling (Throw/TryCatch)
python -m tests.test_type_convert      # Type conversions (ToInt, ToFloat, ToString)
python -m tests.test_wasm_host_print   # WASM host string decoding
```

### Compilation and Execution

```bash
# Compile (auto-detects frontend from env vars: Claude > OpenAI > Gemini > Qwen > mock)
english-compiler compile examples/hello.txt
english-compiler compile --frontend mock examples/hello.txt
english-compiler compile --target python examples/hello.txt

# Run a Core IL file directly
english-compiler run examples/output/coreil/hello.coreil.json

# See all flags and options
english-compiler --help
english-compiler compile --help
```

Note: `python -m english_compiler` also works as an alternative to `english-compiler`.

## Architecture

### Directory Structure

- `english_compiler/` - Main package
  - `coreil/` - Core IL implementation
    - `validate.py` - Core IL validation (structural and semantic)
    - `interp.py` - Reference interpreter (deterministic execution)
    - `emit.py` - Python code generator (transpilation)
    - `emit_javascript.py` - JavaScript code generator
    - `emit_cpp.py` - C++ code generator
    - `emit_rust.py` - Rust code generator
    - `emit_go.py` - Go code generator
    - `emit_assemblyscript.py` - AssemblyScript/WASM code generator
    - `emit_base.py` - Shared codegen base class
    - `optimize.py` - Core IL optimizer (constant folding, DCE, identity simplification)
    - `lint.py` - Static analysis (unused vars, dead code, etc.)
    - `lower.py` - Lowering pass (For/ForEach → While)
    - `source_map.py` - Source map composition (English→CoreIL→target)
    - `debug.py` - Interactive debugger (step-through, breakpoints, variable inspection)
  - `frontend/` - LLM frontends
    - `__init__.py` - Factory function `get_frontend()` for provider selection
    - `base.py` - Abstract base class with shared logic
    - `claude.py` - Claude API integration (Anthropic)
    - `openai_provider.py` - OpenAI API integration
    - `gemini.py` - Google Gemini API integration
    - `qwen.py` - Alibaba Qwen API integration (DashScope or OpenAI-compatible)
    - `mock_llm.py` - Mock generator (deterministic, for testing)
    - `prompt.txt` - System prompt for Core IL generation (shared)
    - `prompt_error.txt` - System prompt for error explanation
    - `error_explainer.py` - LLM-powered error explanation module
    - `experimental/` - Experimental direct compilation mode
    - `coreil_schema.py` - JSON schema for Core IL (shared)
  - `explain.py` - Reverse compiler (Core IL → English explanation)
  - `__main__.py` - CLI entry point

- `tests/` - Test suite (see Testing section above for all modules)
- `examples/` - Example Core IL programs and source files

### Core IL Version Policy

**Current stable version**: Core IL v1.10 (`"coreil-1.10"`)

All versions from v0.1 through v1.10 are supported for backward compatibility. The codebase uses version constants:

```python
from english_compiler.coreil import COREIL_VERSION, SUPPORTED_VERSIONS
```

Version history: v1.0 (frozen core), v1.1 (Record, Set, Deque, Heap, string ops), v1.2 (Math), v1.3/v1.4 (JSON, Regex, string ops consolidated), v1.5 (Slice), v1.6 (MethodCall, PropertyGet — Tier 2), v1.7 (Break, Continue), v1.8 (Throw, TryCatch), v1.9 (ToInt, ToFloat, ToString), v1.10 (Switch).

### Pipeline Stages

1. **Frontend (Non-deterministic)**: Translates English/pseudocode → Core IL JSON. Output cached with source hash in `.lock.json` files.

2. **Core IL (Deterministic)**: Closed specification — all operations explicitly defined. No extension mechanism or helper functions. Validated by `validate.py`. Lowering pass transforms For/ForEach into While loops.

3. **Backends (Deterministic)**: Interpreter, Python, JavaScript, C++, Rust, Go, WASM (AssemblyScript). All backends must produce identical output (verified by tests).

### Artifacts

When compiling `examples/foo.txt`, artifacts go in `examples/output/` organized by type: `coreil/`, `py/`, `js/`, `cpp/`, `wasm/`, `experimental/`. Source maps (`.sourcemap.json`) are written alongside target code when using `--target`.

All `emit_*()` convenience functions return `(code, coreil_line_map)` tuples. Callers that don't need the line map should unpack with `code, _ = emit_python(doc)`.

## Core IL Fundamentals

For the complete Core IL specification and JSON examples, see `coreil_v1.md` and `QUICK_REFERENCE.md`.

### Node Categories

**Expressions** (evaluate to values):
- Literal, Var, Binary, Array, Tuple, Map, Record, Set
- Index, Length, Slice, Get, GetDefault, Keys, GetField, SetHas, SetSize
- StringLength, Substring, CharAt, Join, StringSplit, StringTrim, StringUpper, StringLower, StringStartsWith, StringEndsWith, StringContains, StringReplace
- DequeNew, DequeSize, HeapNew, HeapSize, HeapPeek
- Math, MathPow, MathConst, JsonParse, JsonStringify
- RegexMatch, RegexFindAll, RegexReplace, RegexSplit
- ToInt, ToFloat, ToString (v1.9)
- ExternalCall, MethodCall, PropertyGet (Tier 2 — non-portable, raise error in interpreter)
- Range, Call

**Statements** (perform actions):
- Let, Assign, SetIndex, Set, Push, SetField, SetAdd, SetRemove
- PushBack, PushFront, PopFront, PopBack, HeapPush, HeapPop
- Print, If, While, For, ForEach, Switch
- FuncDef, Return, Break, Continue
- Throw, TryCatch

### Critical Rules

1. **No Helper Functions**: Core IL is sealed. Do not invent helpers like `get_or_default`, `append`, `keys`, `contains`. Use explicit primitives (GetDefault, Push, Keys, SetHas).

2. **Backend Parity**: Interpreter and Python backend must produce identical output. Any divergence is a bug. The algorithm regression tests enforce this.

3. **Short-Circuit Evaluation**: Logical operators (`and`, `or`) must implement proper short-circuiting to prevent runtime errors.

4. **Lowering Pass**: For and ForEach loops are syntax sugar. The lowering pass (`lower.py`) transforms them to While loops before backend execution.

5. **Version Markers**: All core modules (`validate.py`, `interp.py`, `emit.py`) include explicit version markers in docstrings and constants.

## Testing Strategy

### Test Hierarchy

1. **Basic Tests** (`tests.run`): Individual Core IL primitives, interpreter correctness. Fast (~1s).

2. **Algorithm Regression Tests** (`tests.run_algorithms`): Full pipeline validation, backend parity enforcement (interpreter == Python), invalid helper call detection. Golden corpus of 8+ realistic algorithms (~2s).

3. **Specialized Tests** (`tests.test_*`): Feature-specific tests for short-circuit evaluation, lowering, slicing, break/continue, try/catch, type conversion, switch, string ops, records, sets, deques, maps, all backend codegen, source maps, debugger, optimizer, linter, settings, and more.

### Backend Parity Requirements

The interpreter is the reference implementation. When modifying any backend:

1. All algorithm regression tests must pass
2. Interpreter output must exactly match backend output
3. Both must handle the same Core IL constructs
4. Error messages should be consistent

### Adding Tests

**Basic test**: Edit `tests/run.py` and add `_run_example(examples / "new_test.coreil.json", "expected output\n")`

**Algorithm test**: Create `tests/algorithms/new_algorithm.txt` with natural English pseudocode. The test runner auto-discovers `.txt` files.

## Common Pitfalls

1. **Don't bypass validation**: Always call `validate_coreil()` before executing Core IL.
2. **Don't mix node categories**: Expressions cannot contain statements. Use proper nesting.
3. **Don't assume static types**: Core IL uses runtime type checking.
4. **Don't modify v1.0 semantics**: v1.0 is frozen. New features go in v1.1+ with backward compatibility.
5. **Don't skip lowering**: For/ForEach must be lowered before backend execution (happens automatically in `emit_python()`).
6. **Don't invent helper functions**: When LLM generates Core IL, it must use explicit primitives only. Check `english_compiler/frontend/prompt.txt` for the system prompt that enforces this.

## Exit Codes

- `0` - Success
- `1` - Error (I/O, validation failure, runtime error)
- `2` - Ambiguities present (artifacts still written, but user should review)

## Environment Variables

```bash
export ANTHROPIC_API_KEY="..."   # Claude (also ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS)
export OPENAI_API_KEY="..."      # OpenAI (also OPENAI_MODEL, OPENAI_MAX_TOKENS)
export GEMINI_API_KEY="..."      # Gemini (also GEMINI_MODEL)
export QWEN_API_KEY="..."        # Qwen (also QWEN_MODEL, QWEN_MAX_TOKENS, QWEN_BASE_URL)
```

Frontend auto-detection checks for API keys in order: Claude > OpenAI > Gemini > Qwen > mock

## Key Documentation

- `coreil_v1.md` - Complete Core IL v1.0 specification
- `QUICK_REFERENCE.md` - Fast syntax reference with JSON examples
- `STATUS.md` - Project status and capabilities
- `VERSIONING.md` - Version strategy and code hygiene
- `MIGRATION.md` - Upgrade guide from v0.5 to v1.0
- `tests/TESTING_STRATEGY.md` - Detailed testing documentation
- `tests/ALGORITHM_TESTS.md` - Algorithm corpus details
