# English Compiler

A production-ready compiler that translates English pseudocode into executable code through a deterministic intermediate representation (Core IL).

## Installation

```sh
pip install english-compiler
```

With LLM provider support:

```sh
pip install english-compiler[claude]    # Anthropic Claude
pip install english-compiler[openai]    # OpenAI GPT
pip install english-compiler[gemini]    # Google Gemini
pip install english-compiler[qwen]      # Alibaba Qwen
pip install english-compiler[all]       # All providers
```

## Project Status

**Core IL v1.9 is stable and production-ready.**

The compiler has successfully compiled and executed real-world algorithms including:
- Array operations (sum, reverse, max)
- Sorting algorithms (bubble sort)
- String processing (bigram frequency)
- Advanced algorithms (Byte Pair Encoding - 596 lines of Core IL)

All tests pass with 100% parity between interpreter, Python, JavaScript, C++, Rust, Go, and WebAssembly code generation.

**Documentation**:
- [STATUS.md](STATUS.md) - Detailed project status and capabilities
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [MIGRATION.md](MIGRATION.md) - Upgrade guide from earlier versions
- [VERSIONING.md](VERSIONING.md) - Version strategy and code hygiene
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Fast reference for Core IL syntax
- [tests/ALGORITHM_TESTS.md](tests/ALGORITHM_TESTS.md) - Algorithm corpus regression tests

## Quick Start

1) Create a source file:

```sh
echo "Print hello world" > hello.txt
```

2) Compile and run:

```sh
english-compiler compile --frontend mock hello.txt
```

Expected output:

```text
Regenerating Core IL for hello.txt using mock
hello world
```

## CLI Usage

### Version

```sh
english-compiler --version
```

### Compile

```sh
english-compiler compile [options] <source.txt>
```

**Options:**
- `--frontend <provider>`: LLM frontend (`mock`, `claude`, `openai`, `gemini`, `qwen`). Auto-detects based on available API keys if not specified.
- `--target <lang>`: Output target (`coreil`, `python`, `javascript`, `cpp`, `rust`, `go`, `wasm`). Default: `coreil`.
- `--optimize`: Run optimization pass (constant folding, dead code elimination) before codegen.
- `--lint`: Run static analysis after compilation.
- `--regen`: Force regeneration even if cache is valid.
- `--freeze`: Fail if regeneration would be required (useful for CI).

**Output structure:**

When compiling `examples/hello.txt`, artifacts are organized into subdirectories:

```
examples/
├── hello.txt                    # Source file (unchanged)
└── output/
    ├── coreil/
    │   ├── hello.coreil.json    # Core IL (always generated)
    │   └── hello.lock.json      # Cache metadata
    ├── py/
    │   └── hello.py             # With --target python
    ├── js/
    │   └── hello.js             # With --target javascript
    ├── cpp/
    │   ├── hello.cpp            # With --target cpp
    │   ├── coreil_runtime.hpp   # Runtime header
    │   └── json.hpp             # JSON library
    ├── rust/
    │   ├── hello.rs             # With --target rust
    │   └── coreil_runtime.rs    # Runtime library
    ├── go/
    │   ├── hello.go             # With --target go
    │   └── coreil_runtime.go    # Runtime library
    └── wasm/
        ├── hello.as.ts          # With --target wasm
        ├── hello.wasm           # Compiled binary (if asc available)
        └── coreil_runtime.ts    # Runtime library
```

**Examples:**

```sh
# Compile with mock frontend (no API key needed)
english-compiler compile --frontend mock examples/hello.txt

# Compile with Claude and generate Python
english-compiler compile --frontend claude --target python examples/hello.txt

# Auto-detect frontend, generate JavaScript
english-compiler compile --target javascript examples/hello.txt
```

### Explain (Reverse Compile)

Generate a human-readable English explanation of a Core IL program:

```sh
english-compiler explain examples/output/coreil/hello.coreil.json

# More detailed output
english-compiler explain --verbose examples/output/coreil/hello.coreil.json
```

### Run an existing Core IL file

```sh
english-compiler run examples/output/coreil/hello.coreil.json
```

### Lint (Static Analysis)

```sh
# Lint a Core IL file
english-compiler lint myprogram.coreil.json

# Lint with strict mode (warnings become errors)
english-compiler lint --strict myprogram.coreil.json

# Lint after compilation
english-compiler compile --lint --frontend mock examples/hello.txt
```

**Lint rules:**
- `unused-variable` — Variable declared but never referenced
- `unreachable-code` — Statements after Return/Break/Continue/Throw
- `empty-body` — Control flow with empty body
- `variable-shadowing` — Variable re-declared (should be Assign)

### Configuration

Persistent settings can be stored in a config file so you don't need to specify flags on every command.

```sh
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

# View all settings
english-compiler config list

# Show config file path
english-compiler config path

# Reset to defaults
english-compiler config reset
```

**Available settings:**
| Setting | Values | Description |
|---------|--------|-------------|
| `frontend` | `mock`, `claude`, `openai`, `gemini`, `qwen` | Default LLM frontend |
| `target` | `coreil`, `python`, `javascript`, `cpp`, `rust`, `go`, `wasm` | Default compilation target |
| `explain-errors` | `true`, `false` | Enable LLM-powered error explanations |
| `regen` | `true`, `false` | Always force regeneration |
| `freeze` | `true`, `false` | Always fail if regeneration required |

**Config file location:**
- Linux/macOS: `~/.config/english-compiler/config.toml`
- Windows: `~/english-compiler/config.toml`

**Priority:** CLI arguments override config file settings.

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
                          │   v1.9      │  (Deterministic JSON)
                          └──────┬──────┘
                                 │
         ┌──────────┬──────────┼──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │Interp. │ │ Python │ │  Java  │ │  C++   │ │  Rust  │ │   Go   │
    │        │ │Codegen │ │ Script │ │Codegen │ │Codegen │ │Codegen │
    └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
        │          │          │          │          │          │
        └──────────┴──────────┴──────────┴──────────┴──────────┘
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
   - Version 1.9 is the current stable version

3. **Backends**: Deterministic execution
   - Interpreter: Direct execution of Core IL
   - Python codegen: Transpiles to executable Python
   - JavaScript codegen: Transpiles to executable JavaScript
   - C++ codegen: Transpiles to C++17
   - Rust codegen: Transpiles to Rust (single-file, no Cargo needed)
   - Go codegen: Transpiles to Go (single-file with runtime)
   - All backends produce identical output (verified by tests)

## Core IL v1.9

Core IL is a complete, closed intermediate representation with explicit primitives for all operations.

**Full specification**: [coreil_v1.md](coreil_v1.md)

**Key features by version**:

| Version | Features |
|---------|----------|
| v1.9 | ToInt, ToFloat, ToString (type conversions), Go backend, optimizer, explain command |
| v1.8 | Throw, TryCatch (exception handling) |
| v1.7 | Break, Continue (loop control) |
| v1.6 | MethodCall, PropertyGet (Tier 2 OOP), WASM/AssemblyScript backend |
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

When compiling `foo.txt`, artifacts are organized into an `output/` subdirectory:

```
output/
├── coreil/
│   ├── foo.coreil.json    # Core IL (always generated)
│   └── foo.lock.json      # Cache metadata
├── py/foo.py              # With --target python
├── js/foo.js              # With --target javascript
├── cpp/                   # With --target cpp
│   ├── foo.cpp
│   ├── coreil_runtime.hpp
│   └── json.hpp
├── rust/                  # With --target rust
│   ├── foo.rs
│   └── coreil_runtime.rs
├── go/                    # With --target go
│   ├── foo.go
│   └── coreil_runtime.go
└── wasm/                  # With --target wasm
    ├── foo.as.ts
    ├── foo.wasm
    └── coreil_runtime.ts
```

Cache reuse is based on the source hash and Core IL hash.

## Multi-Provider Setup

### Claude (Anthropic)

```sh
pip install english-compiler[claude]

export ANTHROPIC_API_KEY="your_api_key_here"
export ANTHROPIC_MODEL="claude-sonnet-4-5"  # optional
export ANTHROPIC_MAX_TOKENS="4096"           # optional

english-compiler compile --frontend claude examples/hello.txt
```

### OpenAI

```sh
pip install english-compiler[openai]

export OPENAI_API_KEY="your_api_key_here"
export OPENAI_MODEL="gpt-4o"  # optional

english-compiler compile --frontend openai examples/hello.txt
```

### Gemini (Google)

```sh
pip install english-compiler[gemini]

export GOOGLE_API_KEY="your_api_key_here"
export GEMINI_MODEL="gemini-1.5-pro"  # optional

english-compiler compile --frontend gemini examples/hello.txt
```

### Qwen (Alibaba)

```sh
pip install english-compiler[qwen]

export DASHSCOPE_API_KEY="your_api_key_here"
export QWEN_MODEL="qwen-max"  # optional

english-compiler compile --frontend qwen examples/hello.txt
```

## Code Generation

### Python

```sh
english-compiler compile --target python examples/hello.txt
python examples/output/py/hello.py
```

The generated Python code:
- Uses standard Python 3.10+ syntax and semantics
- Matches interpreter output exactly (verified by parity tests)
- Handles all Core IL v1.5 features

### JavaScript

```sh
english-compiler compile --target javascript examples/hello.txt
node examples/output/js/hello.js
```

The generated JavaScript code:
- Uses modern ES6+ syntax
- Runs in Node.js or browsers
- Matches interpreter output exactly

### C++

```sh
english-compiler compile --target cpp examples/hello.txt
g++ -std=c++17 -I examples/output/cpp -o hello examples/output/cpp/hello.cpp && ./hello
```

The generated C++ code:
- Uses C++17 standard
- Includes runtime headers in the same directory
- Matches interpreter output exactly

### Rust

```sh
english-compiler compile --target rust examples/hello.txt
rustc --edition 2021 examples/output/rust/hello.rs -o hello && ./hello
```

The generated Rust code:
- Uses Rust 2021 edition
- Single-file compilation with `rustc` (no Cargo needed)
- Includes runtime library in the same directory
- Matches interpreter output exactly

### Go

```sh
english-compiler compile --target go examples/hello.txt
cd examples/output/go && go mod init prog && go build -o hello . && ./hello
```

The generated Go code:
- Uses Go 1.18+ (standard library only)
- Single-file with runtime library in the same directory
- Matches interpreter output exactly

### WebAssembly

```sh
english-compiler compile --target wasm examples/hello.txt
# Requires: npm install -g assemblyscript
```

The generated WebAssembly:
- Compiles via AssemblyScript (.as.ts)
- Produces .wasm binary if asc compiler is available
- Portable across platforms

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
english-compiler compile --target python examples/external_call_demo.txt

# Run the generated Python
python examples/output/py/external_call_demo.py
```

**Available modules**: `time`, `os`, `fs`, `http`, `crypto`

See [coreil_v1.md](coreil_v1.md) for full ExternalCall documentation.

## Testing

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
- All backends execute successfully (Python, JavaScript, C++, Rust, Go)
- Backend parity (all backend outputs are identical)
- No invalid helper calls

See [tests/ALGORITHM_TESTS.md](tests/ALGORITHM_TESTS.md) for details on failure modes and test coverage.

## Exit codes

- `0`: success
- `1`: error (I/O, validation failure, or runtime error)
- `2`: ambiguities present (artifacts still written)
