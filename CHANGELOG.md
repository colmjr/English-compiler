# Changelog

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
