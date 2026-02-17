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
# Run basic example tests (Core IL primitives and interpreter)
python -m tests.run

# Run algorithm regression tests (full pipeline with backend parity)
python -m tests.run_algorithms

# Run specialized tests
python -m tests.test_short_circuit    # Short-circuit evaluation
python -m tests.test_lower            # Lowering pass (For/ForEach to While)
python -m tests.test_regression_suite # Meta-tests for regression suite
python -m tests.test_lint             # Static analysis (linter) rules
python -m tests.test_rust             # Rust backend codegen + parity
python -m tests.test_go              # Go backend codegen + parity
python -m tests.test_optimize        # Core IL optimizer
python -m tests.test_explain         # Reverse compiler (Core IL → English)
python -m tests.test_wasm_host_print  # WASM host string decoding
python -m tests.test_source_map       # Source map (English→CoreIL→target)
python -m tests.test_debug            # Interactive debugger (step callback, formatting)
python -m tests.test_type_convert     # Type conversions (ToInt, ToFloat, ToString)
```

### Installation

```bash
# Install from PyPI
pip install english-compiler

# With LLM provider support
pip install english-compiler[claude]    # Anthropic Claude
pip install english-compiler[openai]    # OpenAI GPT
pip install english-compiler[gemini]    # Google Gemini
pip install english-compiler[qwen]      # Alibaba Qwen
pip install english-compiler[watch]     # File watching support
pip install english-compiler[all]       # All providers + watch
```

### Compilation and Execution

```bash
# Show version
english-compiler --version

# Compile with auto-detected frontend (checks env vars: Claude > OpenAI > Gemini > Qwen > mock)
english-compiler compile examples/hello.txt

# Compile with explicit frontend selection
english-compiler compile --frontend claude examples/hello.txt
english-compiler compile --frontend openai examples/hello.txt
english-compiler compile --frontend gemini examples/hello.txt
english-compiler compile --frontend qwen examples/hello.txt
english-compiler compile --frontend mock examples/hello.txt

# Generate Python code (in addition to Core IL)
english-compiler compile --target python examples/hello.txt

# Generate other targets
english-compiler compile --target javascript examples/hello.txt
english-compiler compile --target cpp examples/hello.txt
english-compiler compile --target rust examples/hello.txt
english-compiler compile --target go examples/hello.txt
english-compiler compile --target wasm examples/hello.txt

# Compile with optimization pass
english-compiler compile --optimize examples/hello.txt

# Compile with lint (static analysis)
english-compiler compile --lint examples/hello.txt

# Lint an existing Core IL file
english-compiler lint examples/output/coreil/hello.coreil.json
english-compiler lint --strict examples/output/coreil/hello.coreil.json

# Force regeneration (bypass cache)
english-compiler compile --regen examples/hello.txt

# Fail if regeneration required (CI mode)
english-compiler compile --freeze examples/hello.txt

# Explain a Core IL program in English (reverse compile)
english-compiler explain examples/output/coreil/hello.coreil.json
english-compiler explain --verbose examples/output/coreil/hello.coreil.json

# Run an existing Core IL file directly (works with any .coreil.json)
english-compiler run examples/output/coreil/hello.coreil.json

# Run with LLM-powered error explanations (useful for beginners)
english-compiler run --explain-errors examples/output/coreil/hello.coreil.json
english-compiler run --explain-errors --frontend claude examples/output/coreil/hello.coreil.json

# Debug a Core IL file interactively (step through, inspect variables)
english-compiler debug examples/output/coreil/hello.coreil.json

# Compile with error explanations
english-compiler compile --explain-errors examples/hello.txt

# Watch mode (auto-recompile on save)
english-compiler compile --watch examples/hello.txt
english-compiler compile --watch examples/              # watch directory for *.txt files
english-compiler compile --watch --target python examples/hello.txt
english-compiler compile --watch --frontend claude examples/hello.txt
```

### Interactive REPL

```bash
# Start interactive REPL (auto-detect frontend)
english-compiler repl

# REPL with specific frontend
english-compiler repl --frontend claude
english-compiler repl --frontend mock

# REPL with error explanations enabled
english-compiler repl --explain-errors
```

**Exit commands:**
- Built-in: `exit`, `quit`, `:q`, `:quit`, `:exit`
- Signals: `Ctrl+C` (interrupt), `Ctrl+D` (EOF)
- Natural language (LLM-based): "bye", "goodbye", "I'm done", "thanks", etc.

### Experimental Mode (Direct Compilation)

```bash
# EXPERIMENTAL: Compile directly to target without Core IL (non-deterministic)
english-compiler compile --experimental --target python examples/hello.txt
english-compiler compile --experimental --target javascript examples/hello.txt
english-compiler compile --experimental --target cpp examples/hello.txt

# Experimental with explicit frontend selection
english-compiler compile --experimental --frontend claude --target python examples/hello.txt
english-compiler compile --experimental --frontend openai --target javascript examples/hello.txt

# Force regeneration in experimental mode
english-compiler compile --experimental --regen --target python examples/hello.txt
```

**Warning**: Experimental mode bypasses Core IL validation. Output is non-deterministic and may contain bugs. Do not use in production.

Note: `python -m english_compiler` also works as an alternative to `english-compiler`.

### Configuration

Persistent settings can be stored in a config file so you don't need to specify flags on every command.

```bash
# Set default frontend
english-compiler config set frontend claude

# Set default compilation target
english-compiler config set target python

# Enable error explanations by default
english-compiler config set explain-errors true

# Always force regeneration
english-compiler config set regen true

# Always fail if regeneration required (CI mode)
english-compiler config set freeze true

# Get a config value
english-compiler config get frontend

# List all settings
english-compiler config list

# Show config file location
english-compiler config path

# Delete config file (reset to defaults)
english-compiler config reset
```

**Available settings:**
- `frontend` - Default LLM frontend (mock, claude, openai, gemini, qwen)
- `target` - Default compilation target (coreil, python, javascript, cpp, rust, wasm)
- `explain-errors` - Enable LLM-powered error explanations (true/false)
- `regen` - Always force regeneration (true/false)
- `freeze` - Always fail if regeneration required (true/false)

**Config file location:**
- Linux/macOS: `~/.config/english-compiler/config.toml`
- Windows: `~/english-compiler/config.toml` (or via platformdirs if installed)

**Config file format (TOML):**
```toml
[defaults]
frontend = "claude"
target = "python"
explain_errors = true
regen = false
freeze = false
```

**Priority order:** defaults < config file < CLI arguments (CLI always wins)

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
      - `prompts.py` - Prompt loading for direct code generation
      - `validate.py` - Syntax validation (Python only)
      - `prompt_python.txt` - Python generation prompt
      - `prompt_javascript.txt` - JavaScript generation prompt
      - `prompt_cpp.txt` - C++ generation prompt
    - `coreil_schema.py` - JSON schema for Core IL v1.8 (shared)
  - `explain.py` - Reverse compiler (Core IL → English explanation)
  - `__main__.py` - CLI entry point

- `tests/` - Test suite
  - `run.py` - Basic example tests
  - `run_algorithms.py` - Algorithm regression tests
  - `algorithms/` - Natural English algorithm corpus
  - `test_short_circuit.py` - Short-circuit evaluation tests
  - `test_lower.py` - Lowering pass tests
  - `test_regression_suite.py` - Meta-tests
  - `test_lint.py` - Static analysis (linter) rule tests
  - `test_rust.py` - Rust backend codegen and parity tests
  - `test_go.py` - Go backend codegen and parity tests
  - `test_optimize.py` - Core IL optimizer tests
  - `test_explain.py` - Reverse compiler (explain) tests
  - `test_wasm_host_print.py` - WASM host string decoding tests
  - `test_source_map.py` - Source map (English→CoreIL→target) tests
  - `test_debug.py` - Interactive debugger tests
  - `test_type_convert.py` - Type conversion (ToInt, ToFloat, ToString) tests

- `examples/` - Example Core IL programs and source files

### Core IL Version Policy

**Current stable version**: Core IL v1.9 (`"coreil-1.9"`)

Core IL v1.0 is frozen and stable. Core IL v1.1 adds Record, Set (data structure), and string operations. Core IL v1.2 adds portable math operations (Math, MathPow, MathConst). Core IL v1.3 adds JSON operations (JsonParse, JsonStringify) and Regex operations. Core IL v1.4 consolidates Math, JSON, and Regex into a unified version. Core IL v1.5 adds list slicing (Slice expression). Core IL v1.6 adds OOP-style method calls (MethodCall, PropertyGet) for Tier 2 non-portable operations. Core IL v1.7 adds Break and Continue for loop control flow. Core IL v1.8 adds Throw and TryCatch for exception handling. Core IL v1.9 adds type conversion expressions (ToInt, ToFloat, ToString). All versions maintain full backward compatibility.

All versions from v0.1 through v1.9 are supported for backward compatibility. The codebase uses version constants:

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
   - JavaScript codegen: transpiles to executable JavaScript
   - C++ codegen: transpiles to C++17
   - Rust codegen: transpiles to Rust (single-file, no Cargo needed)
   - Go codegen: transpiles to Go (single-file with runtime)
   - WASM codegen: transpiles to AssemblyScript, compiles to WebAssembly
   - All backends must produce identical output (verified by tests)

### Experimental Mode (Direct Compilation)

Experimental mode (`--experimental`) bypasses Core IL entirely:

```
Standard:     English → LLM → Core IL → Validate → Deterministic Backends → .py/.js/.cpp
Experimental: English → LLM → Target Code directly → (syntax check) → .py/.js/.cpp
```

**Key differences:**
- No Core IL intermediate representation
- No semantic validation
- Non-deterministic output (same input may produce different code)
- Only Python syntax is validated (via `ast.parse`); JS/C++ are not validated
- Output goes to `output/experimental/{target}/` with `.exp.lock.json` cache files
- Generated files include warning headers

### Artifacts

When compiling `examples/foo.txt`, artifacts are organized into subdirectories relative to the source file:

```
examples/
├── foo.txt                      (source - unchanged)
└── output/
    ├── coreil/
    │   ├── foo.coreil.json      (Core IL - always generated)
    │   └── foo.lock.json        (cache metadata)
    ├── experimental/            (--experimental mode only)
    │   ├── py/
    │   │   ├── foo.py           (direct LLM output)
    │   │   └── foo.exp.lock.json
    │   ├── js/
    │   │   └── foo.js
    │   └── cpp/
    │       └── foo.cpp
    ├── py/
    │   ├── foo.py               (with --target python)
    │   └── foo.sourcemap.json   (source map, if source_map present)
    ├── js/
    │   └── foo.js               (with --target javascript)
    ├── cpp/
    │   ├── foo.cpp              (with --target cpp)
    │   ├── coreil_runtime.hpp   (runtime header)
    │   └── json.hpp             (JSON library)
    └── wasm/
        ├── foo.as.ts            (with --target wasm)
        ├── foo.wasm             (compiled binary)
        └── coreil_runtime.ts    (runtime library)
```

Cache reuse is based on matching source hash and Core IL hash.

### Source Maps

When compiling with `--target`, a `.sourcemap.json` file is written alongside the target code. It contains three mappings:

```json
{
  "english_to_coreil": {"1": [0, 1, 2], "3": [3, 4]},
  "coreil_to_target": {"0": [1, 2, 3], "1": [4], "2": [5, 6], "3": [7, 8], "4": [9]},
  "english_to_target": {"1": [1, 2, 3, 4, 5, 6], "3": [7, 8, 9]}
}
```

- **english_to_coreil**: From the `source_map` field in `.coreil.json` (produced by LLM frontend). Keys are 1-indexed English line numbers (strings), values are 0-indexed body statement indices.
- **coreil_to_target**: Computed mechanically by the emitter during codegen. Maps body statement indices to output line numbers.
- **english_to_target**: Composed from the above two, giving the full English→target chain.

The `source_map` field in Core IL JSON is optional for backward compatibility. The compose function lives in `english_compiler/coreil/source_map.py`.

All `emit_*()` convenience functions return `(code, coreil_line_map)` tuples. Callers that don't need the line map should unpack with `code, _ = emit_python(doc)`.

## Core IL Fundamentals

### Node Categories

**Expressions** (evaluate to values):
- Literal, Var, Binary, Array, Tuple, Map, Record, Set
- Index, Length, Slice, Get, GetDefault, Keys, GetField, SetHas, SetSize
- StringLength, Substring, CharAt, Join
- DequeNew, DequeSize
- HeapNew, HeapSize, HeapPeek
- Math, MathPow, MathConst
- JsonParse, JsonStringify
- RegexMatch, RegexFindAll, RegexReplace, RegexSplit
- StringSplit, StringTrim, StringUpper, StringLower, StringStartsWith, StringEndsWith, StringContains, StringReplace
- ExternalCall (Tier 2, non-portable)
- MethodCall, PropertyGet (Tier 2, v1.6)
- Range, Call

**Statements** (perform actions):
- Let, Assign, SetIndex, Set, Push, SetField, SetAdd, SetRemove
- PushBack, PushFront, PopFront, PopBack
- HeapPush, HeapPop
- Print, If, While, For, ForEach
- FuncDef, Return
- Break, Continue (v1.7)
- Throw, TryCatch (v1.8)

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
{"type": "SetIndex", "base": <array>, "index": <expr>, "value": <value>}
{"type": "Length", "base": <array>}
{"type": "Slice", "base": <array>, "start": <int>, "end": <int>}
```

Slice extracts elements from index `start` to `end` (exclusive), returning a new list.

**Negative indexing**: Python-style negative indices are supported for `Index`, `SetIndex`, and `Slice`:
- `arr[-1]` → last element (`arr[len(arr) - 1]`)
- `arr[-2]` → second-to-last element
- `arr[-len(arr)]` → first element (`arr[0]`)
- `Slice` with `start: -2, end: 5` on a 5-element array → last 2 elements
- `Slice` with `start: 0, end: -1` → all but the last element
- Out of bounds (e.g., `arr[-(len(arr)+1)]`) raises an error

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

**Deque (double-ended queue - v1.1)**:
```json
{"type": "DequeNew"}
{"type": "DequeSize", "base": <deque>}
{"type": "PushBack", "base": <deque>, "value": <expr>}
{"type": "PushFront", "base": <deque>, "value": <expr>}
{"type": "PopFront", "base": <deque>, "target": "varName"}
{"type": "PopBack", "base": <deque>, "target": "varName"}
```

Note: PopFront and PopBack are statements that assign the popped value to the target variable.

**Loops**:
```json
{"type": "For", "var": "i", "iter": {"type": "Range", "from": 0, "to": 10, "inclusive": false}, "body": [...]}
{"type": "ForEach", "var": "x", "iter": <array_expr>, "body": [...]}
```

**Heap (priority queue - v1.1)**:
```json
{"type": "HeapNew"}
{"type": "HeapSize", "base": <heap>}
{"type": "HeapPeek", "base": <heap>}
{"type": "HeapPush", "base": <heap>, "priority": <num>, "value": <expr>}
{"type": "HeapPop", "base": <heap>, "target": "varName"}
```

**Math operations (v1.2/v1.4)**:
```json
{"type": "Math", "op": "sin|cos|tan|sqrt|floor|ceil|abs|log|exp", "arg": <expr>}
{"type": "MathPow", "base": <expr>, "exponent": <expr>}
{"type": "MathConst", "name": "pi|e"}
```

Supported ops: sin, cos, tan (radians), sqrt, floor, ceil, abs, log (natural), exp (e^x)

**JSON operations (v1.3/v1.4)**:
```json
{"type": "JsonParse", "source": <string>}
{"type": "JsonStringify", "value": <expr>}
{"type": "JsonStringify", "value": <expr>, "pretty": <bool>}
```

**Regex operations (v1.3/v1.4)**:
```json
{"type": "RegexMatch", "string": <str>, "pattern": <str>}
{"type": "RegexFindAll", "string": <str>, "pattern": <str>}
{"type": "RegexReplace", "string": <str>, "pattern": <str>, "replacement": <str>}
{"type": "RegexSplit", "string": <str>, "pattern": <str>}
```

Optional "flags" parameter: "i" (case-insensitive), "m" (multiline), "s" (dotall).

**Loop control (v1.7)**:
```json
{"type": "Break"}
{"type": "Continue"}
```

Break and Continue are only valid inside loops (While, For, ForEach).

**Exception handling (v1.8)**:
```json
{"type": "Throw", "message": <expr>}
{"type": "TryCatch", "body": [<stmts>], "catch_var": "e", "catch_body": [<stmts>], "finally_body": [<stmts>]}
```

- `Throw` raises an error with a message (must evaluate to string)
- `TryCatch` catches both explicit Throw and runtime errors (division by zero, etc.)
- `catch_var` receives the error message as a string
- `finally_body` is optional, always executes
- Control flow (Return, Break, Continue) propagates through — NOT caught

**String operations (v1.4)**:
```json
{"type": "StringSplit", "base": <str>, "delimiter": <str>}
{"type": "StringTrim", "base": <str>}
{"type": "StringUpper", "base": <str>}
{"type": "StringLower", "base": <str>}
{"type": "StringStartsWith", "base": <str>, "prefix": <str>}
{"type": "StringEndsWith", "base": <str>, "suffix": <str>}
{"type": "StringContains", "base": <str>, "substring": <str>}
{"type": "StringReplace", "base": <str>, "old": <str>, "new": <str>}
```

### Operation Tiers

**Tier 1 (Portable)**: All operations above are portable - identical semantics across all platforms.

**Tier 2 (Non-Portable)**: ExternalCall, MethodCall, and PropertyGet enable platform-specific operations. Programs using these cannot run in the interpreter and are marked as non-portable.

**ExternalCall (Tier 2, v1.4)**:
```json
{"type": "ExternalCall", "module": "time", "function": "now", "args": []}
```

Available modules: fs (file system), http, os, crypto, time

**MethodCall (Tier 2, v1.6)** - Call a method on an object:
```json
{"type": "MethodCall", "object": <expr>, "method": "fit", "args": [<expr>, ...]}
```

Example: `model.fit(X, y)` becomes:
```json
{"type": "MethodCall", "object": {"type": "Var", "name": "model"}, "method": "fit", "args": [{"type": "Var", "name": "X"}, {"type": "Var", "name": "y"}]}
```

**PropertyGet (Tier 2, v1.6)** - Access a property on an object:
```json
{"type": "PropertyGet", "object": <expr>, "property": "coef_"}
```

Example: `model.coef_` becomes:
```json
{"type": "PropertyGet", "object": {"type": "Var", "name": "model"}, "property": "coef_"}
```

Notes:
- Tier 2 operations raise an error in the interpreter
- Python/JavaScript/C++ backends generate native code
- Use Tier 1 operations when possible
- MethodCall and PropertyGet enable OOP-style APIs (sklearn, numpy, pandas, etc.)

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

4. **Don't modify v1.0 semantics**: v1.0 is frozen. New features go in v1.1+ (Records, Sets, Deque, Heap), v1.2+ (Math), v1.3+/v1.4+ (JSON, Regex), v1.5+ (Slice), v1.6+ (MethodCall, PropertyGet), v1.7+ (Break, Continue), v1.8+ (Throw, TryCatch), and v1.9+ (ToInt, ToFloat, ToString) with backward compatibility.

5. **Don't skip lowering**: For/ForEach must be lowered before backend execution (happens automatically in `emit_python()`).

6. **Don't invent helper functions**: When LLM generates Core IL, it must use explicit primitives only. Check `english_compiler/frontend/prompt.txt` for the system prompt that enforces this.

## Exit Codes

- `0` - Success
- `1` - Error (I/O, validation failure, runtime error)
- `2` - Ambiguities present (artifacts still written, but user should review)

## Environment Variables

```bash
# Claude API configuration (Anthropic)
export ANTHROPIC_API_KEY="your_api_key"
export ANTHROPIC_MODEL="claude-haiku-4-5-20251001"  # or other model
export ANTHROPIC_MAX_TOKENS="4096"

# OpenAI API configuration
export OPENAI_API_KEY="your_api_key"
export OPENAI_MODEL="gpt-4o"  # or other model
export OPENAI_MAX_TOKENS="4096"

# Google Gemini API configuration
export GEMINI_API_KEY="your_api_key"
export GEMINI_MODEL="gemini-1.5-pro"  # or other model

# Alibaba Qwen API configuration (DashScope)
export QWEN_API_KEY="your_api_key"
export QWEN_MODEL="qwen-turbo"  # or other model
export QWEN_MAX_TOKENS="4096"
# Optional: Use OpenAI-compatible endpoint instead of DashScope
# export QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

Frontend auto-detection checks for API keys in order: Claude > OpenAI > Gemini > Qwen > mock

## Key Documentation

- `coreil_v1.md` - Complete Core IL v1.0 specification
- `STATUS.md` - Project status and capabilities
- `VERSIONING.md` - Version strategy and code hygiene
- `MIGRATION.md` - Upgrade guide from v0.5 to v1.0
- `QUICK_REFERENCE.md` - Fast syntax reference
- `tests/TESTING_STRATEGY.md` - Detailed testing documentation
- `tests/ALGORITHM_TESTS.md` - Algorithm corpus details
