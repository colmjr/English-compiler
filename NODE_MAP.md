# Core IL Node Reference Map

Quick-reference for every Core IL node type: what it does, what fields it has, and where it's implemented.

**Ctrl-F** any node type name (e.g., `GetDefault`, `TryCatch`) to jump to its entry.

**76 node types** across Core IL v0.1–v1.9.

---

## Expressions

### Core

#### Literal
- **Expression** | **v1.0** | **Tier 1**
- A constant value (int, float, string, bool, null)
- **Fields:** `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_literal()` |
| interp.py | `eval_expr()` → `"Literal"` branch |
| emit_base.py | `_emit_literal()` (abstract) |
| emit.py | `PythonEmitter._emit_literal()` |
| emit_javascript.py | `JavaScriptEmitter._emit_literal()` |
| emit_cpp.py | `CppEmitter._emit_literal()` |
| emit_rust.py | `RustEmitter._emit_literal()` |
| emit_go.py | `GoEmitter._emit_literal()` |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_literal()` |
| optimize.py | `_is_literal()` helper; target of constant folding |
| explain.py | `_expr_str()` → `"Literal"` branch |

#### Var
- **Expression** | **v1.0** | **Tier 1**
- Variable reference
- **Fields:** `name`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_var()` |
| interp.py | `eval_expr()` → `"Var"` branch, `lookup_var()` |
| emit_base.py | `_emit_var()` (concrete — returns `node["name"]`) |
| emit.py | inherits `BaseEmitter._emit_var()` |
| emit_javascript.py | inherits `BaseEmitter._emit_var()` |
| emit_cpp.py | inherits `BaseEmitter._emit_var()` |
| emit_rust.py | inherits `BaseEmitter._emit_var()` |
| emit_go.py | inherits `BaseEmitter._emit_var()` |
| emit_assemblyscript.py | inherits `BaseEmitter._emit_var()` |
| optimize.py | passthrough (not optimized) |
| lint.py | `_walk_var_refs()` collects Var references |
| explain.py | `_expr_str()` → `"Var"` branch |

#### Binary
- **Expression** | **v1.0** | **Tier 1**
- Binary operation (arithmetic, comparison, logical)
- **Fields:** `op`, `left`, `right`
- **Operators:** `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`, `>`, `>=`, `and`, `or`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_binary()` |
| interp.py | `eval_expr()` → `"Binary"` branch (short-circuit for `and`/`or`) |
| emit_base.py | `_emit_binary()` (abstract) |
| emit.py | `PythonEmitter._emit_binary()` |
| emit_javascript.py | `JavaScriptEmitter._emit_binary()` |
| emit_cpp.py | `CppEmitter._emit_binary()` |
| emit_rust.py | `RustEmitter._emit_binary()` + `_emit_short_circuit()` |
| emit_go.py | `GoEmitter._emit_binary()` + `_emit_short_circuit()` |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_binary()` |
| optimize.py | `_optimize_expr()` → constant folding (`_try_fold_binary`) + identity simplification (`_try_simplify_identity`) |
| lower.py | `_lower_expr()` → `"Binary"` branch |
| explain.py | `_expr_str()` → `"Binary"` branch |

#### Not
- **Expression** | **v1.5** | **Tier 1**
- Logical negation
- **Fields:** `arg`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_not()` |
| interp.py | `eval_expr()` → `"Not"` branch |
| emit_base.py | `_emit_not()` (abstract) |
| emit.py | `PythonEmitter._emit_not()` |
| emit_javascript.py | `JavaScriptEmitter._emit_not()` |
| emit_cpp.py | `CppEmitter._emit_not()` |
| emit_rust.py | `RustEmitter._emit_not()` |
| emit_go.py | `GoEmitter._emit_not()` |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_not()` |
| optimize.py | `_optimize_expr()` → constant folding on literal arg |
| explain.py | `_expr_str()` → `"Not"` branch |

### Collections

#### Array
- **Expression** | **v1.0** | **Tier 1**
- Array literal
- **Fields:** `items` (list of expressions)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_array()` |
| interp.py | `eval_expr()` → `"Array"` branch |
| emit_base.py | `_emit_array()` (abstract) |
| all emitters | `*Emitter._emit_array()` |
| optimize.py | `_optimize_expr()` → recurse into items |
| lower.py | `_lower_expr()` → `"Array"` branch |
| explain.py | `_expr_str()` → `"Array"` branch |

#### Tuple
- **Expression** | **v1.0** | **Tier 1**
- Immutable, hashable sequence
- **Fields:** `items` (list of expressions)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_tuple()` |
| interp.py | `eval_expr()` → `"Tuple"` branch |
| emit_base.py | `_emit_tuple()` (abstract) |
| all emitters | `*Emitter._emit_tuple()` |
| optimize.py | `_optimize_expr()` → recurse into items |
| explain.py | `_expr_str()` → `"Tuple"` branch |

#### Map
- **Expression** | **v1.0** | **Tier 1**
- Key-value dictionary literal
- **Fields:** `items` (list of `{key, value}` objects)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_map()` |
| interp.py | `eval_expr()` → `"Map"` branch |
| emit_base.py | `_emit_map()` (abstract) |
| all emitters | `*Emitter._emit_map()` |
| optimize.py | `_optimize_expr()` → recurse into key/value pairs |
| lower.py | `_lower_expr()` → `"Map"` branch |
| explain.py | `_expr_str()` → `"Map"` branch |

#### Record
- **Expression** | **v1.1** | **Tier 1**
- Mutable named-field record
- **Fields:** `fields` (list of `{name, value}` objects)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_record()` |
| interp.py | `eval_expr()` → `"Record"` branch |
| emit_base.py | `_emit_record()` (abstract) |
| all emitters | `*Emitter._emit_record()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"Record"` branch |

#### Set
- **Expression + Statement** | **v1.1** | **Tier 1**
- **As expression:** Set literal — `{items: [...]}`
- **As statement:** Map key assignment — `{base, key, value}`
- **Dual-role:** Dispatched as expression when `items` present, as statement when `base`/`key`/`value` present
- **Expression fields:** `items` (list of expressions)
- **Statement fields:** `base`, `key`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_set_expr()` (expr), `_validate_set_stmt()` (stmt) |
| interp.py | `eval_expr()` → `"Set"` expr branch; `exec_stmt()` → `"Set"` stmt branch |
| emit_base.py | `_emit_set_expr()` (expr), `_emit_set_stmt()` (stmt) |
| all emitters | `*Emitter._emit_set_expr()`, `*Emitter._emit_set_stmt()` |
| optimize.py | stmt: optimize base/key/value |
| lower.py | stmt: lower base/key/value |
| explain.py | expr: `_expr_str()` → `"Set"` branch; stmt: `_explain_stmt()` → `"Set"` branch |

### Access

#### Index
- **Expression** | **v1.0** | **Tier 1**
- Array/tuple indexing (supports negative indices)
- **Fields:** `base`, `index`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_index()` |
| interp.py | `eval_expr()` → `"Index"` branch |
| emit_base.py | `_emit_index()` (abstract) |
| all emitters | `*Emitter._emit_index()` |
| optimize.py | `_optimize_expr()` → recurse into base/index |
| lower.py | `_lower_expr()` → `"Index"` branch |
| explain.py | `_expr_str()` → `"Index"` branch |

#### Slice
- **Expression** | **v1.5** | **Tier 1**
- Array slicing (supports negative indices)
- **Fields:** `base`, `start`, `end`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_slice()` |
| interp.py | `eval_expr()` → `"Slice"` branch |
| emit_base.py | `_emit_slice()` (abstract) |
| all emitters | `*Emitter._emit_slice()` |
| optimize.py | `_optimize_expr()` → recurse into base/start/end |
| explain.py | `_expr_str()` → `"Slice"` branch |

#### Length
- **Expression** | **v1.0** | **Tier 1**
- Array/tuple length
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"Length"` branch |
| emit_base.py | `_emit_length()` (abstract) |
| all emitters | `*Emitter._emit_length()` |
| optimize.py | `_optimize_expr()` → recurse into base |
| lower.py | `_lower_expr()` → `"Length"` branch |
| explain.py | `_expr_str()` → `"Length"` branch |

### Map Operations

#### Get
- **Expression** | **v1.0** | **Tier 1**
- Map key lookup (returns null if missing)
- **Fields:** `base`, `key`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_get()` |
| interp.py | `eval_expr()` → `"Get"` branch |
| emit_base.py | `_emit_get()` (abstract) |
| all emitters | `*Emitter._emit_get()` |
| optimize.py | `_optimize_expr()` → recurse into base/key |
| lower.py | `_lower_expr()` → `"Get"` branch |
| explain.py | `_expr_str()` → `"Get"` branch (shared with GetDefault) |

#### GetDefault
- **Expression** | **v1.0** | **Tier 1**
- Map key lookup with fallback value
- **Fields:** `base`, `key`, `default`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_get_default()` |
| interp.py | `eval_expr()` → `"GetDefault"` branch |
| emit_base.py | `_emit_get_default()` (abstract) |
| all emitters | `*Emitter._emit_get_default()` |
| optimize.py | `_optimize_expr()` → recurse into base/key/default |
| explain.py | `_expr_str()` → `"GetDefault"` branch |

#### Keys
- **Expression** | **v1.0** | **Tier 1**
- Map keys as sorted array
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"Keys"` branch |
| emit_base.py | `_emit_keys()` (abstract) |
| all emitters | `*Emitter._emit_keys()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"Keys"` branch |

### Record Operations

#### GetField
- **Expression** | **v1.1** | **Tier 1**
- Record field access
- **Fields:** `base`, `name`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_get_field()` |
| interp.py | `eval_expr()` → `"GetField"` branch |
| emit_base.py | `_emit_get_field()` (abstract) |
| all emitters | `*Emitter._emit_get_field()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"GetField"` branch |

### String Operations

#### StringLength
- **Expression** | **v1.1** | **Tier 1**
- String length
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"StringLength"` branch |
| emit_base.py | `_emit_string_length()` (abstract) |
| all emitters | `*Emitter._emit_string_length()` |
| optimize.py | `_optimize_expr()` → recurse into base |
| explain.py | `_expr_str()` → `"StringLength"` branch |

#### Substring
- **Expression** | **v1.1** | **Tier 1**
- Extract substring by index range
- **Fields:** `base`, `start`, `end`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_substring()` |
| interp.py | `eval_expr()` → `"Substring"` branch |
| emit_base.py | `_emit_substring()` (abstract) |
| all emitters | `*Emitter._emit_substring()` |
| optimize.py | passthrough |
| explain.py | fallback (`<Substring>`) |

#### CharAt
- **Expression** | **v1.1** | **Tier 1**
- Character at index
- **Fields:** `base`, `index`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_char_at()` |
| interp.py | `eval_expr()` → `"CharAt"` branch |
| emit_base.py | `_emit_char_at()` (abstract) |
| all emitters | `*Emitter._emit_char_at()` |
| optimize.py | passthrough |
| explain.py | fallback (`<CharAt>`) |

#### Join
- **Expression** | **v1.1** | **Tier 1**
- Join array items with separator
- **Fields:** `sep`, `items`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_join()` |
| interp.py | `eval_expr()` → `"Join"` branch |
| emit_base.py | `_emit_join()` (abstract) |
| all emitters | `*Emitter._emit_join()` |
| optimize.py | passthrough |
| explain.py | fallback (`<Join>`) |

#### StringSplit
- **Expression** | **v1.4** | **Tier 1**
- Split string by delimiter
- **Fields:** `base`, `delimiter`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_string_split()` |
| interp.py | `eval_expr()` → `"StringSplit"` branch |
| emit_base.py | `_emit_string_split()` (abstract) |
| all emitters | `*Emitter._emit_string_split()` |
| optimize.py | passthrough |

#### StringTrim
- **Expression** | **v1.4** | **Tier 1**
- Trim whitespace from both ends
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"StringTrim"` branch |
| emit_base.py | `_emit_string_trim()` (abstract) |
| all emitters | `*Emitter._emit_string_trim()` |
| optimize.py | `_optimize_expr()` → recurse into base |

#### StringUpper
- **Expression** | **v1.4** | **Tier 1**
- Convert string to uppercase
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"StringUpper"` branch |
| emit_base.py | `_emit_string_upper()` (abstract) |
| all emitters | `*Emitter._emit_string_upper()` |
| optimize.py | `_optimize_expr()` → recurse into base |

#### StringLower
- **Expression** | **v1.4** | **Tier 1**
- Convert string to lowercase
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"StringLower"` branch |
| emit_base.py | `_emit_string_lower()` (abstract) |
| all emitters | `*Emitter._emit_string_lower()` |
| optimize.py | `_optimize_expr()` → recurse into base |

#### StringStartsWith
- **Expression** | **v1.4** | **Tier 1**
- Check if string starts with prefix
- **Fields:** `base`, `prefix`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_string_prefix()` |
| interp.py | `eval_expr()` → `"StringStartsWith"` branch |
| emit_base.py | `_emit_string_starts_with()` (abstract) |
| all emitters | `*Emitter._emit_string_starts_with()` |
| optimize.py | passthrough |

#### StringEndsWith
- **Expression** | **v1.4** | **Tier 1**
- Check if string ends with suffix
- **Fields:** `base`, `suffix`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_string_suffix()` |
| interp.py | `eval_expr()` → `"StringEndsWith"` branch |
| emit_base.py | `_emit_string_ends_with()` (abstract) |
| all emitters | `*Emitter._emit_string_ends_with()` |
| optimize.py | passthrough |

#### StringContains
- **Expression** | **v1.4** | **Tier 1**
- Check if string contains substring
- **Fields:** `base`, `substring`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_string_contains()` |
| interp.py | `eval_expr()` → `"StringContains"` branch |
| emit_base.py | `_emit_string_contains()` (abstract) |
| all emitters | `*Emitter._emit_string_contains()` |
| optimize.py | passthrough |

#### StringReplace
- **Expression** | **v1.4** | **Tier 1**
- Replace all occurrences in string
- **Fields:** `base`, `old`, `new`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_string_replace()` |
| interp.py | `eval_expr()` → `"StringReplace"` branch |
| emit_base.py | `_emit_string_replace()` (abstract) |
| all emitters | `*Emitter._emit_string_replace()` |
| optimize.py | passthrough |

### Set Operations

#### SetHas
- **Expression** | **v1.1** | **Tier 1**
- Set membership test
- **Fields:** `base`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_set_has()` |
| interp.py | `eval_expr()` → `"SetHas"` branch |
| emit_base.py | `_emit_set_has()` (abstract) |
| all emitters | `*Emitter._emit_set_has()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"SetHas"` branch |

#### SetSize
- **Expression** | **v1.1** | **Tier 1**
- Set cardinality
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"SetSize"` branch |
| emit_base.py | `_emit_set_size()` (abstract) |
| all emitters | `*Emitter._emit_set_size()` |
| optimize.py | `_optimize_expr()` → recurse into base |

### Deque Operations

#### DequeNew
- **Expression** | **v1.1** | **Tier 1**
- Create empty deque
- **Fields:** _(none)_
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_no_args()` |
| interp.py | `eval_expr()` → `"DequeNew"` branch |
| emit_base.py | `_emit_deque_new()` (abstract) |
| all emitters | `*Emitter._emit_deque_new()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"DequeNew"` branch |

#### DequeSize
- **Expression** | **v1.1** | **Tier 1**
- Deque element count
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"DequeSize"` branch |
| emit_base.py | `_emit_deque_size()` (abstract) |
| all emitters | `*Emitter._emit_deque_size()` |
| optimize.py | `_optimize_expr()` → recurse into base |

### Heap Operations

#### HeapNew
- **Expression** | **v1.1** | **Tier 1**
- Create empty min-heap
- **Fields:** _(none)_
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_no_args()` |
| interp.py | `eval_expr()` → `"HeapNew"` branch |
| emit_base.py | `_emit_heap_new()` (abstract) |
| all emitters | `*Emitter._emit_heap_new()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"HeapNew"` branch |

#### HeapSize
- **Expression** | **v1.1** | **Tier 1**
- Heap element count
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"HeapSize"` branch |
| emit_base.py | `_emit_heap_size()` (abstract) |
| all emitters | `*Emitter._emit_heap_size()` |
| optimize.py | `_optimize_expr()` → recurse into base |

#### HeapPeek
- **Expression** | **v1.1** | **Tier 1**
- View min element without removing
- **Fields:** `base`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_base_only()` |
| interp.py | `eval_expr()` → `"HeapPeek"` branch |
| emit_base.py | `_emit_heap_peek()` (abstract) |
| all emitters | `*Emitter._emit_heap_peek()` |
| optimize.py | `_optimize_expr()` → recurse into base |

### Math

#### Math
- **Expression** | **v1.2** | **Tier 1**
- Unary math function
- **Fields:** `op` (`sin`, `cos`, `tan`, `sqrt`, `floor`, `ceil`, `abs`, `log`, `exp`), `arg`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_math()` |
| interp.py | `eval_expr()` → `"Math"` branch |
| emit_base.py | `_emit_math()` (abstract) |
| all emitters | `*Emitter._emit_math()` |
| optimize.py | `_optimize_expr()` → recurse into arg |
| explain.py | `_expr_str()` → `"Math"` branch |

#### MathPow
- **Expression** | **v1.2** | **Tier 1**
- Exponentiation
- **Fields:** `base`, `exponent`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_math_pow()` |
| interp.py | `eval_expr()` → `"MathPow"` branch |
| emit_base.py | `_emit_math_pow()` (abstract) |
| all emitters | `*Emitter._emit_math_pow()` |
| optimize.py | `_optimize_expr()` → recurse into base/exponent |
| explain.py | `_expr_str()` → `"MathPow"` branch |

#### MathConst
- **Expression** | **v1.2** | **Tier 1**
- Mathematical constant
- **Fields:** `name` (`pi`, `e`)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_math_const()` |
| interp.py | `eval_expr()` → `"MathConst"` branch |
| emit_base.py | `_emit_math_const()` (abstract) |
| all emitters | `*Emitter._emit_math_const()` |
| optimize.py | passthrough |
| explain.py | `_expr_str()` → `"MathConst"` branch |

### JSON

#### JsonParse
- **Expression** | **v1.3** | **Tier 1**
- Parse JSON string to value
- **Fields:** `source`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_json_parse()` |
| interp.py | `eval_expr()` → `"JsonParse"` branch |
| emit_base.py | `_emit_json_parse()` (abstract) |
| emit.py | `PythonEmitter._emit_json_parse()` |
| emit_javascript.py | `JavaScriptEmitter._emit_json_parse()` |
| emit_cpp.py | `CppEmitter._emit_json_parse()` |
| emit_rust.py | **raises error** (unsupported) |
| emit_go.py | **raises error** (unsupported) |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_json_parse()` |
| optimize.py | passthrough |

#### JsonStringify
- **Expression** | **v1.3** | **Tier 1**
- Convert value to JSON string
- **Fields:** `value`, `pretty` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_json_stringify()` |
| interp.py | `eval_expr()` → `"JsonStringify"` branch |
| emit_base.py | `_emit_json_stringify()` (abstract) |
| emit.py | `PythonEmitter._emit_json_stringify()` |
| emit_javascript.py | `JavaScriptEmitter._emit_json_stringify()` |
| emit_cpp.py | `CppEmitter._emit_json_stringify()` |
| emit_rust.py | **raises error** (unsupported) |
| emit_go.py | **raises error** (unsupported) |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_json_stringify()` |
| optimize.py | passthrough |

### Regex

#### RegexMatch
- **Expression** | **v1.3** | **Tier 1**
- Test if pattern matches string
- **Fields:** `string`, `pattern`, `flags` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_regex_base()` |
| interp.py | `eval_expr()` → `"RegexMatch"` branch |
| emit_base.py | `_emit_regex_match()` (abstract) |
| emit.py | `PythonEmitter._emit_regex_match()` |
| emit_javascript.py | `JavaScriptEmitter._emit_regex_match()` |
| emit_cpp.py | `CppEmitter._emit_regex_match()` |
| emit_rust.py | **raises error** (unsupported) |
| emit_go.py | **raises error** (unsupported) |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_regex_match()` |
| optimize.py | passthrough |

#### RegexFindAll
- **Expression** | **v1.3** | **Tier 1**
- Find all pattern matches
- **Fields:** `string`, `pattern`, `flags` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_regex_base()` |
| interp.py | `eval_expr()` → `"RegexFindAll"` branch |
| emit_base.py | `_emit_regex_find_all()` (abstract) |
| emit.py | `PythonEmitter._emit_regex_find_all()` |
| emit_javascript.py | `JavaScriptEmitter._emit_regex_find_all()` |
| emit_cpp.py | `CppEmitter._emit_regex_find_all()` |
| emit_rust.py | **raises error** (unsupported) |
| emit_go.py | **raises error** (unsupported) |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_regex_find_all()` |
| optimize.py | passthrough |

#### RegexReplace
- **Expression** | **v1.3** | **Tier 1**
- Replace pattern matches
- **Fields:** `string`, `pattern`, `replacement`, `flags` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_regex_replace()` |
| interp.py | `eval_expr()` → `"RegexReplace"` branch |
| emit_base.py | `_emit_regex_replace()` (abstract) |
| emit.py | `PythonEmitter._emit_regex_replace()` |
| emit_javascript.py | `JavaScriptEmitter._emit_regex_replace()` |
| emit_cpp.py | `CppEmitter._emit_regex_replace()` |
| emit_rust.py | **raises error** (unsupported) |
| emit_go.py | **raises error** (unsupported) |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_regex_replace()` |
| optimize.py | passthrough |

#### RegexSplit
- **Expression** | **v1.3** | **Tier 1**
- Split string by regex pattern
- **Fields:** `string`, `pattern`, `flags` (optional), `maxsplit` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_regex_split()` |
| interp.py | `eval_expr()` → `"RegexSplit"` branch |
| emit_base.py | `_emit_regex_split()` (abstract) |
| emit.py | `PythonEmitter._emit_regex_split()` |
| emit_javascript.py | `JavaScriptEmitter._emit_regex_split()` |
| emit_cpp.py | `CppEmitter._emit_regex_split()` |
| emit_rust.py | **raises error** (unsupported) |
| emit_go.py | **raises error** (unsupported) |
| emit_assemblyscript.py | `AssemblyScriptEmitter._emit_regex_split()` |
| optimize.py | passthrough |

### Type Conversion

#### ToInt
- **Expression** | **v1.9** | **Tier 1**
- Convert value to integer
- **Fields:** `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_value_only()` |
| interp.py | `eval_expr()` → `"ToInt"` branch |
| emit_base.py | `_emit_to_int()` (abstract) |
| all emitters | `*Emitter._emit_to_int()` |
| optimize.py | `_optimize_expr()` → recurse into value |
| explain.py | `_expr_str()` → `"ToInt"` branch |

#### ToFloat
- **Expression** | **v1.9** | **Tier 1**
- Convert value to float
- **Fields:** `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_value_only()` |
| interp.py | `eval_expr()` → `"ToFloat"` branch |
| emit_base.py | `_emit_to_float()` (abstract) |
| all emitters | `*Emitter._emit_to_float()` |
| optimize.py | `_optimize_expr()` → recurse into value |
| explain.py | `_expr_str()` → `"ToFloat"` branch |

#### ToString
- **Expression** | **v1.9** | **Tier 1**
- Convert value to string
- **Fields:** `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_value_only()` |
| interp.py | `eval_expr()` → `"ToString"` branch |
| emit_base.py | `_emit_to_string()` (abstract) |
| all emitters | `*Emitter._emit_to_string()` |
| optimize.py | `_optimize_expr()` → recurse into value |
| explain.py | `_expr_str()` → `"ToString"` branch |

### Tier 2 (Non-Portable)

#### ExternalCall
- **Expression** | **v1.4** | **Tier 2**
- Call platform-specific external function
- **Fields:** `module`, `function`, `args`
- **Note:** Raises error in interpreter. Supported in Python and JavaScript backends. Raises error in C++, Rust, Go, and WASM backends.
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_external_call()` |
| interp.py | `eval_expr()` → **raises error** (non-portable) |
| emit_base.py | `_emit_external_call()` (abstract) |
| emit.py | `PythonEmitter._emit_external_call()` |
| emit_javascript.py | `JavaScriptEmitter._emit_external_call()` |
| emit_cpp.py | **raises error** |
| emit_rust.py | **raises error** |
| emit_go.py | **raises error** |
| emit_assemblyscript.py | **raises error** |
| optimize.py | passthrough |

#### MethodCall
- **Expression** | **v1.6** | **Tier 2**
- OOP-style method call on an object
- **Fields:** `object`, `method`, `args`
- **Note:** Raises error in interpreter and WASM backend. Other backends emit native method calls.
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_method_call()` |
| interp.py | `eval_expr()` → **raises error** (non-portable) |
| emit_base.py | `_emit_method_call()` (abstract) |
| emit.py | `PythonEmitter._emit_method_call()` |
| emit_javascript.py | `JavaScriptEmitter._emit_method_call()` |
| emit_cpp.py | `CppEmitter._emit_method_call()` |
| emit_rust.py | `RustEmitter._emit_method_call()` |
| emit_go.py | `GoEmitter._emit_method_call()` |
| emit_assemblyscript.py | **raises error** |
| optimize.py | passthrough |

#### PropertyGet
- **Expression** | **v1.6** | **Tier 2**
- OOP-style property access on an object
- **Fields:** `object`, `property`
- **Note:** Raises error in interpreter and WASM backend. Other backends emit native property access.
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_property_get()` |
| interp.py | `eval_expr()` → **raises error** (non-portable) |
| emit_base.py | `_emit_property_get()` (abstract) |
| emit.py | `PythonEmitter._emit_property_get()` |
| emit_javascript.py | `JavaScriptEmitter._emit_property_get()` |
| emit_cpp.py | `CppEmitter._emit_property_get()` |
| emit_rust.py | `RustEmitter._emit_property_get()` |
| emit_go.py | `GoEmitter._emit_property_get()` |
| emit_assemblyscript.py | **raises error** |
| optimize.py | passthrough |

### Control

#### Range
- **Expression** | **v1.0** | **Tier 1**
- Integer range (only valid inside `For.iter`)
- **Fields:** `from`, `to`, `inclusive` (optional, default false)
- **Note:** Not a general-purpose expression. Only valid as the `iter` field of a `For` statement.
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_range()` |
| interp.py | evaluated inline in `For` handler |
| emit_base.py | not in dispatch table (handled by `_emit_for()`) |
| all emitters | handled inside `*Emitter._emit_for()` |
| optimize.py | `_optimize_expr()` → recurse into from/to |
| lower.py | `_lower_expr()` → `"Range"` branch (preserved) |
| explain.py | `_expr_str()` → `"Range"` branch |

#### Call
- **Expression + Statement** | **v1.0** | **Tier 1**
- Function call (user-defined or builtin)
- **Fields:** `name`, `args`
- **Dual-role:** Can appear as both an expression (returns value) and a statement (discards return value)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_call_expr()` / `_validate_call_stmt()` (checks disallowed helpers in sealed versions) |
| interp.py | `eval_expr()` → `call_any()`; `exec_stmt()` → `call_any()` |
| emit_base.py | `_emit_call_expr()` (abstract), `_emit_call_stmt()` (abstract) |
| all emitters | `*Emitter._emit_call_expr()`, `*Emitter._emit_call_stmt()` |
| optimize.py | `_optimize_expr()` → recurse into args; `_optimize_stmt()` → recurse into args |
| lower.py | `_lower_expr()` → `"Call"` branch; `_lower_statement()` → `"Call"` branch |
| explain.py | `_expr_str()` → `"Call"` branch; `_explain_stmt()` → `"Call"` branch |

---

## Statements

### Variables

#### Let
- **Statement** | **v1.0** | **Tier 1**
- Variable declaration (introduces new binding)
- **Fields:** `name`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_let()` |
| interp.py | `exec_stmt()` → `"Let"` branch |
| emit_base.py | `_emit_let()` (abstract) |
| all emitters | `*Emitter._emit_let()` |
| optimize.py | `_optimize_stmt()` → optimize value |
| lower.py | `_lower_statement()` → `"Let"` branch |
| lint.py | triggers `unused-variable` and `variable-shadowing` checks |
| debug.py | `_format_stmt()` → `"Let"` branch |
| explain.py | `_explain_stmt()` → `"Let"` branch |

#### Assign
- **Statement** | **v1.0** | **Tier 1**
- Variable reassignment
- **Fields:** `name`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_assign()` |
| interp.py | `exec_stmt()` → `"Assign"` branch |
| emit_base.py | `_emit_assign()` (abstract) |
| all emitters | `*Emitter._emit_assign()` |
| optimize.py | `_optimize_stmt()` → optimize value |
| lower.py | `_lower_statement()` → `"Assign"` branch |
| debug.py | `_format_stmt()` → `"Assign"` branch |
| explain.py | `_explain_stmt()` → `"Assign"` branch |

### I/O

#### Print
- **Statement** | **v1.0** | **Tier 1**
- Print values to stdout
- **Fields:** `args` (list of expressions)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_print_stmt()` / `_validate_print_expr()` |
| interp.py | `exec_stmt()` → `"Print"` branch |
| emit_base.py | `_emit_print()` (abstract) |
| all emitters | `*Emitter._emit_print()` |
| optimize.py | `_optimize_stmt()` → optimize args |
| lower.py | `_lower_statement()` → `"Print"` branch |
| debug.py | `_format_stmt()` → `"Print"` branch |
| explain.py | `_explain_stmt()` → `"Print"` branch |

### Control Flow

#### If
- **Statement** | **v1.0** | **Tier 1**
- Conditional branch
- **Fields:** `test`, `then` (body), `else` (optional body)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_if()` |
| interp.py | `exec_stmt()` → `"If"` branch |
| emit_base.py | `_emit_if()` (abstract) |
| all emitters | `*Emitter._emit_if()` |
| optimize.py | `_optimize_stmt()` → optimize test + DCE on constant condition |
| lower.py | `_lower_statement()` → lower test/then/else |
| lint.py | `empty-body` check on `then`/`else` |
| debug.py | `_format_stmt()` → `"If"` branch |
| explain.py | `_explain_stmt()` → `"If"` branch |

#### While
- **Statement** | **v1.0** | **Tier 1**
- While loop
- **Fields:** `test`, `body`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_while()` |
| interp.py | `exec_stmt()` → `"While"` branch (handles Break/Continue) |
| emit_base.py | `_emit_while()` (abstract) |
| all emitters | `*Emitter._emit_while()` |
| optimize.py | `_optimize_stmt()` → optimize test/body |
| lower.py | `_lower_statement()` → lower test/body |
| lint.py | `empty-body` check |
| debug.py | `_format_stmt()` → `"While"` branch |
| explain.py | `_explain_stmt()` → `"While"` branch |

#### For
- **Statement** | **v1.0** | **Tier 1**
- Counted for loop (with Range iterator)
- **Fields:** `var`, `iter` (usually Range), `body`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_for()` |
| interp.py | `exec_stmt()` → `"For"` branch (handles Break/Continue) |
| emit_base.py | `_emit_for()` (abstract) |
| all emitters | `*Emitter._emit_for()` |
| optimize.py | `_optimize_stmt()` → optimize iter/body |
| lower.py | `_lower_for()` (preserves For, lowers sub-expressions) |
| lint.py | `empty-body` check |
| debug.py | `_format_stmt()` → `"For"` branch |
| explain.py | `_explain_stmt()` → `"For"` branch |

#### ForEach
- **Statement** | **v1.0** | **Tier 1**
- Iterate over array/tuple elements
- **Fields:** `var`, `iter`, `body`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_for_each()` |
| interp.py | `exec_stmt()` → `"ForEach"` branch (handles Break/Continue) |
| emit_base.py | `_emit_for_each()` (abstract) |
| all emitters | `*Emitter._emit_for_each()` |
| optimize.py | `_optimize_stmt()` → optimize iter/body |
| lower.py | `_lower_foreach()` (preserves ForEach, lowers sub-expressions) |
| lint.py | `empty-body` check |
| debug.py | `_format_stmt()` → `"ForEach"` branch |
| explain.py | `_explain_stmt()` → `"ForEach"` branch |

#### FuncDef
- **Statement** | **v1.0** | **Tier 1**
- Function definition
- **Fields:** `name`, `params`, `body`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_func_def()` |
| interp.py | `exec_stmt()` → `"FuncDef"` branch (registers in `functions` dict) |
| emit_base.py | `_emit_func_def()` (abstract) |
| all emitters | `*Emitter._emit_func_def()` |
| optimize.py | `_optimize_stmt()` → optimize body |
| lower.py | `_lower_statement()` → lower body |
| debug.py | `_format_stmt()` → `"FuncDef"` branch |
| explain.py | `_explain_stmt()` → `"FuncDef"` branch |

#### Return
- **Statement** | **v1.0** | **Tier 1**
- Return from function
- **Fields:** `value` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_return()` (validates `in_func` context) |
| interp.py | `exec_stmt()` → `"Return"` branch (raises `_ReturnSignal`) |
| emit_base.py | `_emit_return()` (abstract) |
| all emitters | `*Emitter._emit_return()` |
| optimize.py | `_optimize_stmt()` → optimize value; triggers DCE |
| lower.py | `_lower_statement()` → lower value |
| debug.py | `_format_stmt()` → `"Return"` branch |
| explain.py | `_explain_stmt()` → `"Return"` branch |

#### Break
- **Statement** | **v1.7** | **Tier 1**
- Break out of loop
- **Fields:** _(none)_
- **Note:** Only valid inside While, For, or ForEach.
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_break()` (validates `in_loop` context) |
| interp.py | `exec_stmt()` → raises `_BreakSignal` |
| emit_base.py | `_emit_break()` (abstract) |
| all emitters | `*Emitter._emit_break()` |
| optimize.py | triggers DCE (dead code after Break) |
| lint.py | terminates unreachable-code detection |
| debug.py | `_format_stmt()` → `"Break"` branch |
| explain.py | `_explain_stmt()` → `"Break"` branch |

#### Continue
- **Statement** | **v1.7** | **Tier 1**
- Skip to next loop iteration
- **Fields:** _(none)_
- **Note:** Only valid inside While, For, or ForEach.
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_continue()` (validates `in_loop` context) |
| interp.py | `exec_stmt()` → raises `_ContinueSignal` |
| emit_base.py | `_emit_continue()` (abstract) |
| all emitters | `*Emitter._emit_continue()` |
| optimize.py | triggers DCE (dead code after Continue) |
| lint.py | terminates unreachable-code detection |
| debug.py | `_format_stmt()` → `"Continue"` branch |
| explain.py | `_explain_stmt()` → `"Continue"` branch |

### Exceptions

#### Throw
- **Statement** | **v1.8** | **Tier 1**
- Raise an error with a message
- **Fields:** `message`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_throw()` |
| interp.py | `exec_stmt()` → raises `_ThrowSignal` |
| emit_base.py | `_emit_throw()` (abstract) |
| all emitters | `*Emitter._emit_throw()` |
| optimize.py | `_optimize_stmt()` → optimize message; triggers DCE |
| lower.py | `_lower_statement()` → lower message |
| debug.py | `_format_stmt()` → `"Throw"` branch |
| explain.py | `_explain_stmt()` → `"Throw"` branch |

#### TryCatch
- **Statement** | **v1.8** | **Tier 1**
- Exception handling block
- **Fields:** `body`, `catch_var`, `catch_body`, `finally_body` (optional)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_try_catch()` |
| interp.py | `exec_stmt()` → `"TryCatch"` branch (catches `_ThrowSignal` and runtime errors; propagates Return/Break/Continue) |
| emit_base.py | `_emit_try_catch()` (abstract) |
| all emitters | `*Emitter._emit_try_catch()` |
| optimize.py | `_optimize_stmt()` → optimize body/catch_body/finally_body |
| lower.py | `_lower_statement()` → lower body/catch_body/finally_body |
| lint.py | `empty-body` check on body/catch_body/finally_body |
| debug.py | `_format_stmt()` → `"TryCatch"` branch |
| explain.py | `_explain_stmt()` → `"TryCatch"` branch |

### Mutation

#### SetIndex
- **Statement** | **v1.0** | **Tier 1**
- Array element assignment (supports negative indices)
- **Fields:** `base`, `index`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_set_index()` |
| interp.py | `exec_stmt()` → `"SetIndex"` branch |
| emit_base.py | `_emit_set_index()` (abstract) |
| all emitters | `*Emitter._emit_set_index()` |
| optimize.py | `_optimize_stmt()` → optimize base/index/value |
| lower.py | `_lower_statement()` → lower base/index/value |
| debug.py | `_format_stmt()` → `"SetIndex"` branch |
| explain.py | `_explain_stmt()` → `"SetIndex"` branch |

#### Push
- **Statement** | **v1.0** | **Tier 1**
- Append value to array
- **Fields:** `base`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_push()` |
| interp.py | `exec_stmt()` → `"Push"` branch |
| emit_base.py | `_emit_push()` (abstract) |
| all emitters | `*Emitter._emit_push()` |
| optimize.py | `_optimize_stmt()` → optimize base/value |
| debug.py | `_format_stmt()` → `"Push"` branch |
| explain.py | `_explain_stmt()` → `"Push"` branch |

#### SetField
- **Statement** | **v1.1** | **Tier 1**
- Record field assignment
- **Fields:** `base`, `name`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_set_field()` |
| interp.py | `exec_stmt()` → `"SetField"` branch |
| emit_base.py | `_emit_set_field()` (abstract) |
| all emitters | `*Emitter._emit_set_field()` |
| optimize.py | `_optimize_stmt()` → optimize base/value |
| debug.py | `_format_stmt()` → `"SetField"` branch |
| explain.py | `_explain_stmt()` → `"SetField"` branch |

#### SetAdd
- **Statement** | **v1.1** | **Tier 1**
- Add item to set
- **Fields:** `base`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_set_add()` |
| interp.py | `exec_stmt()` → `"SetAdd"` branch |
| emit_base.py | `_emit_set_add()` (abstract) |
| all emitters | `*Emitter._emit_set_add()` |
| optimize.py | `_optimize_stmt()` → optimize base/value |

#### SetRemove
- **Statement** | **v1.1** | **Tier 1**
- Remove item from set (no-op if absent)
- **Fields:** `base`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_set_remove()` |
| interp.py | `exec_stmt()` → `"SetRemove"` branch |
| emit_base.py | `_emit_set_remove()` (abstract) |
| all emitters | `*Emitter._emit_set_remove()` |
| optimize.py | `_optimize_stmt()` → optimize base/value |

### Deque Mutations

#### PushBack
- **Statement** | **v1.1** | **Tier 1**
- Append to back of deque
- **Fields:** `base`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_push_back()` |
| interp.py | `exec_stmt()` → `"PushBack"` branch |
| emit_base.py | `_emit_push_back()` (abstract) |
| all emitters | `*Emitter._emit_push_back()` |
| optimize.py | `_optimize_stmt()` → optimize base/value |

#### PushFront
- **Statement** | **v1.1** | **Tier 1**
- Prepend to front of deque
- **Fields:** `base`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_push_front()` |
| interp.py | `exec_stmt()` → `"PushFront"` branch |
| emit_base.py | `_emit_push_front()` (abstract) |
| all emitters | `*Emitter._emit_push_front()` |
| optimize.py | `_optimize_stmt()` → optimize base/value |

#### PopFront
- **Statement** | **v1.1** | **Tier 1**
- Remove and assign front element
- **Fields:** `base`, `target` (variable name to assign)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_pop_front()` |
| interp.py | `exec_stmt()` → `"PopFront"` branch |
| emit_base.py | `_emit_pop_front()` (abstract) |
| all emitters | `*Emitter._emit_pop_front()` |
| optimize.py | `_optimize_stmt()` → optimize base |

#### PopBack
- **Statement** | **v1.1** | **Tier 1**
- Remove and assign back element
- **Fields:** `base`, `target` (variable name to assign)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_pop_back()` |
| interp.py | `exec_stmt()` → `"PopBack"` branch |
| emit_base.py | `_emit_pop_back()` (abstract) |
| all emitters | `*Emitter._emit_pop_back()` |
| optimize.py | `_optimize_stmt()` → optimize base |

### Heap Mutations

#### HeapPush
- **Statement** | **v1.1** | **Tier 1**
- Push value with priority onto min-heap
- **Fields:** `base`, `priority`, `value`
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_heap_push()` |
| interp.py | `exec_stmt()` → `"HeapPush"` branch |
| emit_base.py | `_emit_heap_push()` (abstract) |
| all emitters | `*Emitter._emit_heap_push()` |
| optimize.py | `_optimize_stmt()` → optimize base/priority/value |

#### HeapPop
- **Statement** | **v1.1** | **Tier 1**
- Pop min element and assign to variable
- **Fields:** `base`, `target` (variable name to assign)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_heap_pop()` |
| interp.py | `exec_stmt()` → `"HeapPop"` branch |
| emit_base.py | `_emit_heap_pop()` (abstract) |
| all emitters | `*Emitter._emit_heap_pop()` |
| optimize.py | `_optimize_stmt()` → optimize base |

### Switch

#### Switch
- **Statement** | **v1.8** | **Tier 1**
- Multi-way branch
- **Fields:** `test`, `cases` (list of `{value, body}`), `default` (optional body)
- **Implementations:**

| Module | Handler |
|--------|---------|
| validate.py | `_validate_switch()` |
| interp.py | `exec_stmt()` → `"Switch"` branch |
| emit_base.py | `_emit_switch()` (abstract) |
| all emitters | `*Emitter._emit_switch()` |
| optimize.py | `_optimize_stmt()` → optimize test/cases/default |
| lower.py | `_lower_statement()` → lower test/cases/default |
| lint.py | recurse into case bodies and default |
| debug.py | `_format_stmt()` → `"Switch"` branch |
| explain.py | `_explain_stmt()` → `"Switch"` branch |

---

## Coverage Matrix

Compact view: which modules handle which node types. **E** = expression handler, **S** = statement handler, **B** = both.

| Node | validate | interp | emit_base | py | js | cpp | rust | go | wasm | optimize | lower | lint | debug | explain |
|------|----------|--------|-----------|----|----|-----|------|----|------|----------|-------|------|-------|---------|
| Literal | E | E | E | E | E | E | E | E | E | target | - | - | - | E |
| Var | E | E | E | E | E | E | E | E | E | - | - | ref | - | E |
| Binary | E | E | E | E | E | E | E | E | E | fold+id | E | - | - | E |
| Not | E | E | E | E | E | E | E | E | E | fold | - | - | - | E |
| Array | E | E | E | E | E | E | E | E | E | items | E | - | - | E |
| Tuple | E | E | E | E | E | E | E | E | E | items | - | - | - | E |
| Map | E | E | E | E | E | E | E | E | E | items | E | - | - | E |
| Record | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| Set (expr) | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| Index | E | E | E | E | E | E | E | E | E | base | E | - | - | E |
| Slice | E | E | E | E | E | E | E | E | E | base | - | - | - | E |
| Length | E | E | E | E | E | E | E | E | E | base | E | - | - | E |
| Get | E | E | E | E | E | E | E | E | E | base | E | - | - | E |
| GetDefault | E | E | E | E | E | E | E | E | E | base | - | - | - | E |
| Keys | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| GetField | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| StringLength | E | E | E | E | E | E | E | E | E | base | - | - | - | E |
| Substring | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| CharAt | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| Join | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| StringSplit | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| StringTrim | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| StringUpper | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| StringLower | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| StringStartsWith | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| StringEndsWith | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| StringContains | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| StringReplace | E | E | E | E | E | E | E | E | E | - | - | - | - | - |
| SetHas | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| SetSize | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| DequeNew | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| DequeSize | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| HeapNew | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| HeapSize | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| HeapPeek | E | E | E | E | E | E | E | E | E | base | - | - | - | - |
| Math | E | E | E | E | E | E | E | E | E | arg | - | - | - | E |
| MathPow | E | E | E | E | E | E | E | E | E | base | - | - | - | E |
| MathConst | E | E | E | E | E | E | E | E | E | - | - | - | - | E |
| JsonParse | E | E | E | E | E | E | err | err | E | - | - | - | - | - |
| JsonStringify | E | E | E | E | E | E | err | err | E | - | - | - | - | - |
| RegexMatch | E | E | E | E | E | E | err | err | E | - | - | - | - | - |
| RegexFindAll | E | E | E | E | E | E | err | err | E | - | - | - | - | - |
| RegexReplace | E | E | E | E | E | E | err | err | E | - | - | - | - | - |
| RegexSplit | E | E | E | E | E | E | err | err | E | - | - | - | - | - |
| ToInt | E | E | E | E | E | E | E | E | E | value | - | - | - | E |
| ToFloat | E | E | E | E | E | E | E | E | E | value | - | - | - | E |
| ToString | E | E | E | E | E | E | E | E | E | value | - | - | - | E |
| ExternalCall | E | err | E | E | E | err | err | err | err | - | - | - | - | - |
| MethodCall | E | err | E | E | E | E | E | E | err | - | - | - | - | - |
| PropertyGet | E | err | E | E | E | E | E | E | err | - | - | - | - | - |
| Range | E | inline | - | - | - | - | - | - | - | from/to | E | - | - | E |
| Call | B | B | B | B | B | B | B | B | B | args | B | - | S | B |
| Let | S | S | S | S | S | S | S | S | S | value | S | decl | S | S |
| Assign | S | S | S | S | S | S | S | S | S | value | S | ref | S | S |
| Print | S | S | S | S | S | S | S | S | S | args | S | - | S | S |
| If | S | S | S | S | S | S | S | S | S | DCE | S | body | S | S |
| While | S | S | S | S | S | S | S | S | S | body | S | body | S | S |
| For | S | S | S | S | S | S | S | S | S | body | S | body | S | S |
| ForEach | S | S | S | S | S | S | S | S | S | body | S | body | S | S |
| FuncDef | S | S | S | S | S | S | S | S | S | body | S | scope | S | S |
| Return | S | S | S | S | S | S | S | S | S | DCE | S | term | S | S |
| Set (stmt) | S | S | S | S | S | S | S | S | S | base | S | - | S | S |
| SetIndex | S | S | S | S | S | S | S | S | S | base | S | - | S | S |
| Push | S | S | S | S | S | S | S | S | S | base | - | - | S | S |
| SetField | S | S | S | S | S | S | S | S | S | base | - | - | S | S |
| SetAdd | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| SetRemove | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| PushBack | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| PushFront | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| PopFront | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| PopBack | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| HeapPush | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| HeapPop | S | S | S | S | S | S | S | S | S | base | - | - | - | - |
| Break | S | S | S | S | S | S | S | S | S | DCE | - | term | S | S |
| Continue | S | S | S | S | S | S | S | S | S | DCE | - | term | S | S |
| Throw | S | S | S | S | S | S | S | S | S | DCE | S | term | S | S |
| TryCatch | S | S | S | S | S | S | S | S | S | body | S | body | S | S |
| Switch | S | S | S | S | S | S | S | S | S | body | S | body | S | S |

**Legend:** E = expression, S = statement, B = both, err = raises error, inline = handled inline in parent, target = optimization target, fold = constant folding, fold+id = constant folding + identity simplification, items/base/args/value/body/from/to/arg = recurse into those fields, DCE = dead code elimination trigger, ref = variable reference tracking, decl = declaration tracking, term = terminator for unreachable-code rule, body = empty-body check, scope = scope analysis

---

## Dispatch Patterns

### validate.py

Two dispatch tables — `_EXPR_VALIDATORS` and `_STMT_VALIDATORS` — map node type strings to validator functions. Special case: `Call` is handled inline (needs `version` argument for helper-function checking).

```python
_EXPR_VALIDATORS = {"Literal": _validate_literal, "Var": _validate_var, ...}
_STMT_VALIDATORS = {"Let": _validate_let, "Assign": _validate_assign, ...}
```

### interp.py

Two monolithic if/elif chains in `eval_expr()` (expressions) and `exec_stmt()` (statements). No dispatch table — direct string comparison on `node["type"]`.

### emit_base.py

Two dispatch tables in `_setup_dispatch_tables()`: `self.expr_handlers` and `self.stmt_handlers`. All handlers are abstract methods that subclasses must implement.

```python
self.expr_handlers = {"Literal": self._emit_literal, ...}
self.stmt_handlers = {"Let": self._emit_let, ...}
```

### emit.py / emit_javascript.py / emit_cpp.py / emit_rust.py / emit_go.py / emit_assemblyscript.py

All inherit from `BaseEmitter`. Override every abstract method. Dispatch happens through the base class tables.

### optimize.py

Two monolithic if/elif chains in `_optimize_expr()` and `_optimize_stmt()`. Unrecognized nodes pass through unchanged.

### lint.py

Pattern-matching on `stype` in `_check_block()`. Uses `_TERMINATOR_TYPES` set and `_BODY_CONTAINERS` dict for structural checks.

### lower.py

Pattern-matching on `node_type` in `_lower_statement()` and `_lower_expr()`. Unrecognized statements pass through as `[stmt]`. Unrecognized expressions pass through unchanged.

### debug.py

`_format_stmt()` uses if/elif chain on `stype` for one-line summaries. Only handles statements (no expression formatting).

### explain.py

`_expr_str()` and `_explain_stmt()` use if/elif chains on node type. Unrecognized expressions fall back to `<TypeName>`, unrecognized statements show `[TypeName statement]`.
