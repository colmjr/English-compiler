# Changelog

## Post-v1.9 Features - 2026-02-17

### LLM Error Recovery with Retry

- **Enhanced retry logic**: When the LLM produces invalid Core IL, the compiler now retries up to 3 times (configurable via `max_retries` parameter)
- **Full context on retry**: Retry messages include the complete previous Core IL output and validation errors, giving the LLM maximum context to fix issues
- **Large output truncation**: Core IL outputs over 30KB are truncated in retry messages to respect context limits
- **New test suite**: `python -m tests.test_retry` — 8 tests covering retry behavior and message formatting

### Property-Based Fuzzing

- **New test suite**: `python -m tests.test_fuzz` generates random valid Core IL programs and checks parity across interpreter, Python, and JavaScript backends
- **Configurable**: `--count N` for iteration count, `--seed N` for reproducibility
- **Random program generator**: Produces programs with For/While loops, If/Else, functions, arrays, binary ops, and more
- **Verified**: 200+ random programs pass with full backend parity

---

## Post-v1.8 Features - 2026-02-15

### Rust Backend

- **New backend**: `--target rust` transpiles Core IL to Rust
  - Single-file compilation with `rustc` (no Cargo needed)
  - Dynamic typing via `Value` enum with `Rc<RefCell<T>>` for mutable containers
  - Full support for all Core IL v1.8 features (except JSON/Regex which are deferred)
  - Python-compatible output formatting
  - Included in backend parity test suite

### Static Analysis (`--lint`)

- **New command**: `english-compiler lint <file>` for static analysis on Core IL programs
  - `unused-variable` — Variable declared but never referenced
  - `unreachable-code` — Statements after Return/Break/Continue/Throw
  - `empty-body` — Control flow with empty body
  - `variable-shadowing` — Variable re-declared (should be Assign)
  - `--strict` mode turns warnings into errors (exit code 1)
  - `--lint` flag on `compile` command runs lint after compilation

### WASM Backend Fixes

- Fixed `__host_print` to properly read AssemblyScript strings from WASM linear memory (UTF-16LE decoding)
- Updated WASM runtime version marker from v1.5 to v1.8
- WASM backend now testable end-to-end when `asc` compiler is available

---

## Core IL v1.8 - 2026-02-15

**Status: Stable and Production Ready**

### New Features

- **Throw**: Raise runtime errors with a message
  - `{"type": "Throw", "message": <expr>}`
  - Message must evaluate to a string

- **TryCatch**: Exception handling with try/catch/finally
  - `{"type": "TryCatch", "body": [...], "catch_var": "e", "catch_body": [...], "finally_body": [...]}`
  - Catches both explicit `Throw` errors and runtime errors (division by zero, index out of bounds, etc.)
  - `catch_var` receives the error message as a string
  - `finally_body` is optional and always executes
  - Control flow signals (Return, Break, Continue) propagate through — they are NOT caught

### Backend Support

- All backends (Interpreter, Python, JavaScript, C++, Rust, WASM/AssemblyScript) support v1.8 features
- C++ backend simulates `finally` using `std::exception_ptr`
- Rust backend uses `std::panic::catch_unwind` for exception handling
- 100% parity maintained across all backends

---

## Core IL v1.7 - 2026-02-10

**Status: Stable**

### New Features

- **Break**: Exit a loop early
  - `{"type": "Break"}`
  - Only valid inside While, For, or ForEach loops

- **Continue**: Skip to next loop iteration
  - `{"type": "Continue"}`
  - Only valid inside While, For, or ForEach loops

---

## Core IL v1.6 - 2026-02-01

**Status: Stable**

### New Features

- **MethodCall**: Call a method on an object (Tier 2, non-portable)
  - `{"type": "MethodCall", "object": <expr>, "method": "fit", "args": [<expr>, ...]}`
  - Enables OOP-style APIs (sklearn, numpy, pandas, etc.)

- **PropertyGet**: Access a property on an object (Tier 2, non-portable)
  - `{"type": "PropertyGet", "object": <expr>, "property": "coef_"}`

### New Backends

- **WASM/AssemblyScript Codegen**: Generates AssemblyScript code compiled to WebAssembly
  - Runs via Node.js with AssemblyScript toolchain
  - Full parity with interpreter for Tier 1 operations

---

## Core IL v1.5 - 2026-01-26

**Status: Stable and Production Ready**

### New Features

- **Slice**: Extract a sublist from an array using start and end indices
  - `{"type": "Slice", "base": <array>, "start": <expr>, "end": <expr>}`
  - End index is exclusive (Python-style slicing)

- **Not**: Unary logical negation operator
  - `{"type": "Not", "value": <expr>}`
  - Returns boolean negation of the value

- **Negative Indexing**: Python-style negative indices for array access
  - `arr[-1]` returns the last element
  - Works with Index and Slice operations

### Backend Improvements

- All backends (Interpreter, Python, JavaScript, C++) support v1.5 features
- 100% parity maintained across all backends

---

## Core IL v1.4 - 2026-01-20

**Status: Stable**

### New Features

- **ExternalCall**: Platform-specific function calls (Tier 2, non-portable)
  - Enables file I/O, HTTP requests, system calls
  - Only supported in Python backend
  - Available modules: `time`, `os`, `fs`, `http`, `crypto`

- **Expanded String Operations**:
  - `StringSplit` - Split string by delimiter
  - `StringTrim` - Remove leading/trailing whitespace
  - `StringUpper` - Convert to uppercase
  - `StringLower` - Convert to lowercase
  - `StringReplace` - Replace substring occurrences
  - `StringContains` - Check if string contains substring
  - `StringStartsWith` - Check string prefix
  - `StringEndsWith` - Check string suffix

### New Backends

- **JavaScript Codegen**: Generates ES6+ JavaScript code
  - Runs in Node.js or browsers
  - Full parity with interpreter

- **C++ Codegen**: Generates C++17 code
  - Native performance
  - Full parity with interpreter

### New Frontends

- **OpenAI**: GPT-4 and GPT-4o support
- **Gemini**: Google Gemini support
- **Qwen**: Alibaba Qwen support

---

## Core IL v1.3 - 2026-01-15

**Status: Stable**

### New Features

- **JSON Operations**:
  - `JsonParse` - Parse JSON string to Core IL value
  - `JsonStringify` - Convert value to JSON string

- **Regex Operations**:
  - `RegexMatch` - Test if string matches pattern
  - `RegexFindAll` - Find all matches of pattern in string
  - `RegexReplace` - Replace pattern matches in string
  - `RegexSplit` - Split string by regex pattern

---

## Core IL v1.2 - 2026-01-12

**Status: Stable**

### New Features

- **Math Operations**:
  - `Math` - Unary math functions (sin, cos, tan, sqrt, floor, ceil, abs, log, exp)
  - `MathPow` - Power function (base^exponent)
  - `MathConst` - Math constants (pi, e)

---

## Core IL v1.1 - 2026-01-11

**Status: Stable**

### New Features

- **Record**: Mutable named fields for structured data
  - `Record` - Create a record with named fields
  - `GetField` - Access a record field
  - `SetField` - Update a record field

- **Set** (data structure): Unordered collection of unique elements
  - `Set` - Create a set from items
  - `SetHas` - Check if item is in set
  - `SetAdd` - Add item to set
  - `SetRemove` - Remove item from set
  - `SetSize` - Get number of items in set

- **Deque**: Double-ended queue
  - `DequeNew` - Create empty deque
  - `DequeSize` - Get deque size
  - `PushBack` - Add to back
  - `PushFront` - Add to front
  - `PopBack` - Remove from back (statement, assigns to target)
  - `PopFront` - Remove from front (statement, assigns to target)

- **Heap**: Min-heap priority queue
  - `HeapNew` - Create empty heap
  - `HeapSize` - Get heap size
  - `HeapPeek` - View minimum element
  - `HeapPush` - Add element
  - `HeapPop` - Remove minimum (statement, assigns to target)

- **String Operations**:
  - `StringLength` - Get string length
  - `Substring` - Extract substring
  - `CharAt` - Get character at index
  - `Join` - Join array elements into string

---

## Core IL v1.0 - 2026-01-10

**Status: Stable and Frozen**

This release marks the first stable, production-ready version of Core IL. The specification is frozen and all existing tests pass with 100% parity between interpreter and Python code generation.

### Major Changes

- **Formalized Specification**: Created comprehensive [coreil_v1.md](coreil_v1.md) documenting all node types, semantics, and invariants
- **Short-Circuit Evaluation**: Implemented proper short-circuit evaluation for `and` and `or` operators (critical bug fix)
- **Tuple Support**: Enhanced interpreter and codegen to support tuple indexing and length operations
- **Dictionary Keys**: Fixed Keys operation to use insertion order instead of sorted order (supports mixed-type keys)
- **Version Support**: All components now accept `"coreil-1.0"` as a valid version string

### Breaking Changes

None. Core IL v1.0 is fully backward compatible with v0.5. Programs written in v0.5 work in v1.0 without modification.

### Bug Fixes

1. **Short-Circuit Evaluation** ([english_compiler/coreil/interp.py](english_compiler/coreil/interp.py))
   - **Problem**: The interpreter evaluated both operands of `and`/`or` operators before checking the operator, causing runtime errors when the right side accessed out-of-bounds indices
   - **Solution**: Implemented proper short-circuit evaluation - `and` returns false without evaluating right side when left is falsy, `or` returns true without evaluating right side when left is truthy
   - **Impact**: Enables safe guard patterns like `i < len(arr) and arr[i] == value`

2. **Tuple Indexing** ([english_compiler/coreil/interp.py](english_compiler/coreil/interp.py))
   - **Problem**: Index and Length operations only accepted lists, rejecting tuples
   - **Solution**: Updated type checks to accept both `list` and `tuple` (both are Python sequences)
   - **Impact**: Tuples can now be indexed and measured, essential for algorithms using tuples as structured data

3. **Mixed-Type Dictionary Keys** ([english_compiler/coreil/emit.py](english_compiler/coreil/emit.py))
   - **Problem**: Keys operation used `sorted()` which fails on mixed-type keys like `(20, 10)` and `(1, "r1")`
   - **Solution**: Changed from `sorted(dict.keys())` to `list(dict.keys())` to preserve insertion order
   - **Impact**: Dictionaries with heterogeneous tuple keys now work correctly (e.g., BPE algorithm)

### Testing

All test suites pass:
- `python -m tests.run` - Core interpreter and validation tests
- `python -m tests.test_short_circuit` - Short-circuit evaluation tests
- `python -m tests.run_algorithms` - Algorithm regression tests

Successfully tested with real-world algorithms:
- Array operations (sum, reverse, max, bubble sort)
- String processing (bigram frequency)
- Advanced algorithms (Byte Pair Encoding with 596-line Core IL)

### Documentation

- **[coreil_v1.md](coreil_v1.md)**: Complete specification with philosophy, all node types, semantics, examples, and implementation requirements
- **[README.md](README.md)**: Updated to reflect v1.0 status and architecture

### Future Work

Core IL v1.0 is feature-complete and frozen. Extensions are added in v1.1+.

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
