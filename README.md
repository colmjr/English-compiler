# English Compiler

A production-ready compiler that translates English pseudocode into executable code through a deterministic intermediate representation (Core IL).

## Project Status

**Core IL v1.5 is stable and production-ready.**

The compiler has successfully compiled and executed real-world algorithms including:
- Array operations (sum, reverse, max)
- Sorting algorithms (bubble sort)
- String processing (bigram frequency)
- Advanced algorithms (Byte Pair Encoding - 596 lines of Core IL)

All tests pass with 100% parity between interpreter, Python, JavaScript, and C++ code generation.

**Documentation**:
- [STATUS.md](STATUS.md) - Detailed project status and capabilities
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [MIGRATION.md](MIGRATION.md) - Upgrade guide from earlier versions
- [VERSIONING.md](VERSIONING.md) - Version strategy and code hygiene
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Fast reference for Core IL syntax
- [tests/ALGORITHM_TESTS.md](tests/ALGORITHM_TESTS.md) - Algorithm corpus regression tests

## Requirements

- Python 3.10+
- Standard library for core functionality
- Optional LLM provider SDKs:
  - `pip install anthropic` for Claude
  - `pip install openai` for OpenAI
  - `pip install google-generativeai` for Gemini
  - `pip install dashscope` for Qwen

## Quick start (mock frontend)

1) Create a source file:

```sh
printf "hello\n" > examples/hello.txt
```

2) Compile and run:

```sh
python -m english_compiler compile --frontend mock examples/hello.txt
```

Expected output:

```text
Regenerating Core IL for examples/hello.txt
hello
```

## CLI usage

### Compile

```sh
python -m english_compiler compile [--frontend mock|claude|openai|gemini|qwen] [--target coreil|python|javascript|cpp] [--regen] [--freeze] <source.txt>
```

Behavior:
- Produces `foo.coreil.json` and `foo.lock.json` next to the source file.
- When `--target python` is specified, also generates `foo.py` with executable Python code.
- When `--target javascript` is specified, generates `foo.js` with executable JavaScript code.
- When `--target cpp` is specified, generates `foo.cpp` with C++ code.
- Uses cached artifacts if they match the source hash.
- Exits `2` and prints ambiguity details when `ambiguities` is non-empty.

Flags:
- `--frontend mock`: use the mocked generator (default when no API key).
- `--frontend claude`: use Anthropic Claude (requires `ANTHROPIC_API_KEY`).
- `--frontend openai`: use OpenAI GPT (requires `OPENAI_API_KEY`).
- `--frontend gemini`: use Google Gemini (requires `GOOGLE_API_KEY`).
- `--frontend qwen`: use Alibaba Qwen (requires `DASHSCOPE_API_KEY`).
- `--target coreil`: only emit Core IL JSON (default).
- `--target python`: emit both Core IL JSON and Python code.
- `--target javascript`: emit both Core IL JSON and JavaScript code.
- `--target cpp`: emit both Core IL JSON and C++ code.
- `--regen`: force regeneration even if cache is valid.
- `--freeze`: fail if regeneration would be required.

### Run an existing Core IL file

```sh
python -m english_compiler run examples/hello.coreil.json
```

## Architecture

The compiler follows a three-stage pipeline:

```
                              ┌─────────────┐
                              │   English   │
                              │  Pseudocode │
                              └──────┬──────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │           LLM Frontends                  │
              │  Claude | OpenAI | Gemini | Qwen | Mock  │
              │         (Non-deterministic)              │
              └──────────────────┬───────────────────────┘
                                 │
                                 ▼
                          ┌─────────────┐
                          │  Core IL    │
                          │   v1.5      │  (Deterministic JSON)
                          └──────┬──────┘
                                 │
         ┌───────────┬───────────┼───────────┬───────────┐
         ▼           ▼           ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │Interpret│ │ Python  │ │  Java   │ │   C++   │
    │   er    │ │ Codegen │ │ Script  │ │ Codegen │
    └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
         │           │           │           │
         └───────────┴───────────┴───────────┘
                           │
                           ▼
                   Identical Output
                 (Verified by tests)
```

1. **Frontend (LLM)**: Multiple providers translate English/pseudocode into Core IL JSON
   - This is the only non-deterministic step
   - Output is cached for reproducibility

2. **Core IL**: A closed, deterministic intermediate representation
   - All semantics are explicitly defined
   - No extension mechanism or helper functions
   - Version 1.5 is the current stable version

3. **Backends**: Deterministic execution
   - Interpreter: Direct execution of Core IL
   - Python codegen: Transpiles to executable Python
   - JavaScript codegen: Transpiles to executable JavaScript
   - C++ codegen: Transpiles to C++
   - All backends produce identical output (verified by tests)

## Core IL v1.5

Core IL is a complete, closed intermediate representation with explicit primitives for all operations.

**Full specification**: [coreil_v1.md](coreil_v1.md)

**Key features by version**:

| Version | Features |
|---------|----------|
| v1.5 | Slice, Not (unary), negative indexing |
| v1.4 | ExternalCall (Tier 2), expanded string operations, JS/C++ backends |
| v1.3 | JsonParse, JsonStringify, Regex operations |
| v1.2 | Math, MathPow, MathConst |
| v1.1 | Record, Set, Deque, Heap, basic string operations |
| v1.0 | Short-circuit evaluation, Tuple, sealed primitives (frozen) |

**Core v1.0 features** (stable, frozen):
- Expressions: Literal, Var, Binary, Array, Tuple, Map, Index, Length, Get, GetDefault, Keys, Range, Call
- Statements: Let, Assign, SetIndex, Set, Push, Print, If, While, For, ForEach, FuncDef, Return
- Short-circuit evaluation for logical operators (`and`, `or`)
- Runtime type checking with clear error messages
- Recursion support with depth limits
- Dictionary insertion order preservation

## Artifacts

When compiling `foo.txt`, the following files are created:

- `foo.coreil.json`: Core IL program (always generated)
- `foo.lock.json`: cache metadata (hashes, model, timestamp)
- `foo.py`: executable Python code (only when `--target python` is used)
- `foo.js`: executable JavaScript code (only when `--target javascript` is used)
- `foo.cpp`: C++ code (only when `--target cpp` is used)

Cache reuse is based on the source hash and Core IL hash.

## Multi-Provider Setup

### Claude (Anthropic)

```sh
python -m pip install anthropic

export ANTHROPIC_API_KEY="your_api_key_here"
export ANTHROPIC_MODEL="claude-sonnet-4-5"  # optional
export ANTHROPIC_MAX_TOKENS="4096"           # optional

python -m english_compiler compile --frontend claude examples/hello.txt
```

### OpenAI

```sh
python -m pip install openai

export OPENAI_API_KEY="your_api_key_here"
export OPENAI_MODEL="gpt-4o"  # optional

python -m english_compiler compile --frontend openai examples/hello.txt
```

### Gemini (Google)

```sh
python -m pip install google-generativeai

export GOOGLE_API_KEY="your_api_key_here"
export GEMINI_MODEL="gemini-1.5-pro"  # optional

python -m english_compiler compile --frontend gemini examples/hello.txt
```

### Qwen (Alibaba)

```sh
python -m pip install dashscope

export DASHSCOPE_API_KEY="your_api_key_here"
export QWEN_MODEL="qwen-max"  # optional

python -m english_compiler compile --frontend qwen examples/hello.txt
```

## Demo script

Run the Claude demo (prints a generated Core IL JSON object):

```sh
python -m scripts.demo_claude_compile
```

## Code Generation

### Python

```sh
python -m english_compiler compile --target python examples/hello.txt
python examples/hello.py
```

The generated Python code:
- Uses standard Python 3.10+ syntax and semantics
- Matches interpreter output exactly (verified by parity tests)
- Handles all Core IL v1.5 features

### JavaScript

```sh
python -m english_compiler compile --target javascript examples/hello.txt
node examples/hello.js
```

The generated JavaScript code:
- Uses modern ES6+ syntax
- Runs in Node.js or browsers
- Matches interpreter output exactly

### C++

```sh
python -m english_compiler compile --target cpp examples/hello.txt
g++ -std=c++17 -o hello examples/hello.cpp && ./hello
```

The generated C++ code:
- Uses C++17 standard
- Includes all necessary headers
- Matches interpreter output exactly

## ExternalCall (Tier 2 operations)

Core IL v1.4+ supports ExternalCall for platform-specific operations like file I/O, HTTP requests, and system calls. These are **non-portable** and only work with the Python backend (not the interpreter).

**Example**: Get current timestamp and working directory

```json
{
  "version": "coreil-1.5",
  "body": [
    {
      "type": "Let",
      "name": "timestamp",
      "value": {
        "type": "ExternalCall",
        "module": "time",
        "function": "time",
        "args": []
      }
    },
    {
      "type": "Print",
      "args": [{"type": "Literal", "value": "Timestamp:"}, {"type": "Var", "name": "timestamp"}]
    }
  ]
}
```

**Running ExternalCall programs**:

```sh
# Compile to Python (required for ExternalCall)
python -m english_compiler compile --target python examples/external_call_demo.coreil.json

# Run the generated Python
python examples/external_call_demo.py
```

**Available modules**: `time`, `os`, `fs`, `http`, `crypto`

See [coreil_v1.md](coreil_v1.md) for full ExternalCall documentation.

### Testing

**Basic tests** (examples in `examples/` directory):
```sh
python -m tests.run
```

**Algorithm regression tests** (golden corpus with backend parity):
```sh
python -m tests.run_algorithms
```

This enforces:
- Core IL validation passes
- Interpreter executes successfully
- Python backend executes successfully
- Backend parity (interpreter output == Python output)
- No invalid helper calls

See [tests/ALGORITHM_TESTS.md](tests/ALGORITHM_TESTS.md) for details on failure modes and test coverage.

## Exit codes

- `0`: success
- `1`: error (I/O, validation failure, or runtime error)
- `2`: ambiguities present (artifacts still written)
