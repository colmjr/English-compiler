"""JavaScript code generator for Core IL.

This file implements Core IL v1.8 to JavaScript (ES Modules) transpilation.
Core IL v1.8 adds TryCatch and Throw for exception handling.

The generated JavaScript code:
- Matches interpreter semantics exactly
- Uses ES Module format
- Preserves Map/Object insertion order
- Implements short-circuit evaluation naturally
- Record support (mutable named fields)
- Set operations (membership, add, remove, size)
- Deque operations (double-ended queue using arrays)
- Heap operations (min-heap priority queue with inline class)
- Math operations (sin, cos, tan, sqrt, floor, ceil, abs, log, exp, pow, pi, e)
- JSON operations (parse, stringify)
- Regex operations (match, findall, replace, split)
- Array slicing (Slice)
- Unary not (Not)
- Break and Continue loop control
- OOP-style method calls and property access (Tier 2)
- Imports Node.js modules only for Tier 2 ExternalCall operations

Version history:
- v1.7: Added Break and Continue loop control statements
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2, non-portable)
- v1.5: Added Slice for array/list slicing, Not for logical negation
- v1.4: Initial JavaScript backend (matching Python emit.py)

Backward compatibility: Accepts v0.1 through v1.8 programs.
"""

from __future__ import annotations

from english_compiler.coreil.emit_base import BaseEmitter


# Map Core IL external module names to Node.js imports
_EXTERNAL_MODULE_MAP = {
    "fs": "fs",
    "http": "http",
    "os": "os",
    "crypto": "crypto",
    "time": None,  # Uses Date built-in
}


class JavaScriptEmitter(BaseEmitter):
    """JavaScript code emitter for Core IL."""

    @property
    def indent_str(self) -> str:
        return "  "

    def _setup_state(self) -> None:
        """Initialize JavaScript-specific state."""
        self.uses_heap = False
        self.uses_tuple_set = False
        self.uses_regex_flags = False
        self.uses_print = False
        self.uses_float = False
        self.uses_index = False  # Track if we need index helper for negative indexing
        self.external_modules: set[str] = set()

    def emit(self) -> str:
        """Generate JavaScript code from Core IL document."""
        body = self.doc.get("body", [])
        for stmt in body:
            self.emit_stmt(stmt)

        return self._build_output()

    def _build_output(self) -> str:
        """Build final output with imports and helpers."""
        header_lines: list[str] = []

        # Add external module imports for Tier 2
        if self.external_modules:
            header_lines.append("// External module imports (Tier 2 - non-portable)")
            for module in sorted(self.external_modules):
                js_module = _EXTERNAL_MODULE_MAP.get(module)
                if js_module:
                    header_lines.append(f"import {module} from '{js_module}';")

            # Add external call dispatcher
            header_lines.append("")
            header_lines.append("// External call dispatcher")
            header_lines.append("const __external = {")
            if "time" in self.external_modules:
                header_lines.append("  time: {")
                header_lines.append("    now: () => Date.now() / 1000,")
                header_lines.append("    sleep: (ms) => new Promise(r => setTimeout(r, ms * 1000)),")
                header_lines.append("  },")
            if "os" in self.external_modules:
                header_lines.append("  os: {")
                header_lines.append("    env: (name) => process.env[name] ?? null,")
                header_lines.append("    cwd: () => process.cwd(),")
                header_lines.append("    argv: () => process.argv,")
                header_lines.append("    exit: (code) => process.exit(code),")
                header_lines.append("  },")
            if "fs" in self.external_modules:
                header_lines.append("  fs: {")
                header_lines.append("    readFile: (path) => fs.readFileSync(path, 'utf-8'),")
                header_lines.append("    writeFile: (path, content) => fs.writeFileSync(path, content, 'utf-8'),")
                header_lines.append("    exists: (path) => fs.existsSync(path),")
                header_lines.append("  },")
            if "crypto" in self.external_modules:
                header_lines.append("  crypto: {")
                header_lines.append("    hash: (data) => crypto.createHash('sha256').update(data).digest('hex'),")
                header_lines.append("  },")
            if "http" in self.external_modules:
                header_lines.append("  http: {")
                header_lines.append("    get: (url) => { throw new Error('http.get not implemented'); },")
                header_lines.append("  },")
            header_lines.append("};")

        # Add heap class if needed
        if self.uses_heap:
            if header_lines:
                header_lines.append("")
            header_lines.extend(self._heap_class_lines())

        # Add regex flags helper if needed
        if self.uses_regex_flags:
            if header_lines:
                header_lines.append("")
            header_lines.extend(self._regex_flags_helper_lines())

        # Add float wrapper for Math operations
        if self.uses_float:
            if header_lines:
                header_lines.append("")
            header_lines.extend(self._float_wrapper_lines())

        # Add print helper for Python-compatible output format
        if self.uses_print:
            if header_lines:
                header_lines.append("")
            header_lines.extend(self._print_helper_lines())

        # Add index helpers for Python-style negative indexing
        if self.uses_index:
            if header_lines:
                header_lines.append("")
            header_lines.extend(self._index_helper_lines())

        # Add warning comment for non-portable programs
        if self.external_modules:
            warning = [
                "// WARNING: This program uses external calls and is NOT PORTABLE",
                f"// Required external modules: {', '.join(sorted(self.external_modules))}",
            ]
            header_lines = warning + [""] + header_lines

        if header_lines:
            header_lines.append("")
            result = "\n".join(header_lines) + "\n".join(self.lines) + "\n"
        else:
            result = "\n".join(self.lines) + "\n"

        return result

    def _heap_class_lines(self) -> list[str]:
        """Return lines for the heap class definition."""
        return [
            "// Min-heap implementation for Core IL Heap operations",
            "class __CoreILHeap {",
            "  constructor() {",
            "    this._items = [];",
            "    this._counter = 0;",
            "  }",
            "  push(priority, value) {",
            "    const entry = [priority, this._counter++, value];",
            "    this._items.push(entry);",
            "    this._siftUp(this._items.length - 1);",
            "  }",
            "  pop() {",
            "    if (this._items.length === 0) throw new Error('heap is empty');",
            "    const result = this._items[0][2];",
            "    const last = this._items.pop();",
            "    if (this._items.length > 0) {",
            "      this._items[0] = last;",
            "      this._siftDown(0);",
            "    }",
            "    return result;",
            "  }",
            "  peek() {",
            "    if (this._items.length === 0) throw new Error('heap is empty');",
            "    return this._items[0][2];",
            "  }",
            "  size() { return this._items.length; }",
            "  _siftUp(i) {",
            "    while (i > 0) {",
            "      const parent = Math.floor((i - 1) / 2);",
            "      if (this._cmp(this._items[i], this._items[parent]) < 0) {",
            "        [this._items[i], this._items[parent]] = [this._items[parent], this._items[i]];",
            "        i = parent;",
            "      } else break;",
            "    }",
            "  }",
            "  _siftDown(i) {",
            "    const n = this._items.length;",
            "    while (true) {",
            "      let smallest = i;",
            "      const left = 2 * i + 1, right = 2 * i + 2;",
            "      if (left < n && this._cmp(this._items[left], this._items[smallest]) < 0) smallest = left;",
            "      if (right < n && this._cmp(this._items[right], this._items[smallest]) < 0) smallest = right;",
            "      if (smallest === i) break;",
            "      [this._items[i], this._items[smallest]] = [this._items[smallest], this._items[i]];",
            "      i = smallest;",
            "    }",
            "  }",
            "  _cmp(a, b) {",
            "    if (a[0] !== b[0]) return a[0] - b[0];",
            "    return a[1] - b[1];",
            "  }",
            "}",
        ]

    def _regex_flags_helper_lines(self) -> list[str]:
        """Return lines for the regex flags helper."""
        return [
            "// Regex flags parser",
            "function __parseRegexFlags(flags) {",
            "  let result = '';",
            "  if (flags && flags.includes('i')) result += 'i';",
            "  if (flags && flags.includes('m')) result += 'm';",
            "  if (flags && flags.includes('s')) result += 's';",
            "  return result;",
            "}",
        ]

    def _float_wrapper_lines(self) -> list[str]:
        """Return lines for the float wrapper class."""
        return [
            "// Float wrapper to preserve Python-like float formatting",
            "class __Float {",
            "  constructor(v) { this.value = v; }",
            "  valueOf() { return this.value; }",
            "  toString() {",
            "    if (Number.isInteger(this.value)) return this.value + '.0';",
            "    return String(this.value);",
            "  }",
            "}",
            "function __float(v) { return new __Float(v); }",
        ]

    def _print_helper_lines(self) -> list[str]:
        """Return lines for the print helper function."""
        lines = [
            "// Print helper for Python-compatible output",
            "function __format(v) {",
            "  if (v === true) return 'True';",
            "  if (v === false) return 'False';",
            "  if (v === null) return 'None';",
        ]
        if self.uses_float:
            lines.append("  if (v instanceof __Float) return v.toString();")
        lines.extend([
            "  if (Array.isArray(v)) return '[' + v.map(__format).join(', ') + ']';",
            "  return v;",
            "}",
            "function __print(...args) {",
            "  console.log(args.map(__format).join(' '));",
            "}",
        ])
        return lines

    def _index_helper_lines(self) -> list[str]:
        """Return lines for index helper functions (Python-style negative indexing)."""
        return [
            "// Index helpers for Python-style negative indexing",
            "function __idx(arr, i) {",
            "  if (i < 0) i = arr.length + i;",
            "  if (i < 0 || i >= arr.length) throw new Error('Index out of range');",
            "  return arr[i];",
            "}",
            "function __setIdx(arr, i, v) {",
            "  if (i < 0) i = arr.length + i;",
            "  if (i < 0 || i >= arr.length) throw new Error('Index out of range');",
            "  arr[i] = v;",
            "}",
        ]

    # ========== Expression Handlers ==========

    def _emit_literal(self, node: dict) -> str:
        value = node.get("value")
        if isinstance(value, str):
            escaped = self.escape_string(value)
            return f'"{escaped}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif value is None:
            return "null"
        else:
            return str(value)

    def _emit_binary(self, node: dict) -> str:
        op = node.get("op")
        left = self.emit_expr(node.get("left"))
        right = self.emit_expr(node.get("right"))
        if op == "and":
            return f"({left} && {right})"
        elif op == "or":
            return f"({left} || {right})"
        elif op == "==":
            return f"({left} === {right})"
        elif op == "!=":
            return f"({left} !== {right})"
        elif op == "//":
            return f"Math.floor({left} / {right})"
        elif op == "%":
            return f"((({left}) % ({right})) + ({right})) % ({right})"
        else:
            return f"({left} {op} {right})"

    def _emit_array(self, node: dict) -> str:
        items = node.get("items", [])
        item_strs = [self.emit_expr(item) for item in items]
        return f"[{', '.join(item_strs)}]"

    def _emit_index(self, node: dict) -> str:
        self.uses_index = True
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        return f"__idx({base}, {index})"

    def _emit_slice(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        start = self.emit_expr(node.get("start"))
        end = self.emit_expr(node.get("end"))
        return f"{base}.slice({start}, {end})"

    def _emit_not(self, node: dict) -> str:
        arg = self.emit_expr(node.get("arg"))
        return f"(!{arg})"

    def _emit_length(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.length"

    def _emit_call_expr(self, node: dict) -> str:
        name = node.get("name")
        args = node.get("args", [])

        if name == "get_or_default":
            if len(args) != 3:
                raise ValueError(f"get_or_default expects 3 arguments, got {len(args)}")
            d = self.emit_expr(args[0])
            k = self.emit_expr(args[1])
            default = self.emit_expr(args[2])
            return f"({d}.get({k}) ?? {default})"

        if name == "entries":
            if len(args) != 1:
                raise ValueError(f"entries expects 1 argument, got {len(args)}")
            d = self.emit_expr(args[0])
            return f"Array.from({d}.entries())"

        if name == "append":
            if len(args) != 2:
                raise ValueError(f"append expects 2 arguments, got {len(args)}")
            lst = self.emit_expr(args[0])
            value = self.emit_expr(args[1])
            return f"({lst}.push({value}), null)"

        arg_strs = [self.emit_expr(arg) for arg in args]
        return f"{name}({', '.join(arg_strs)})"

    def _emit_map(self, node: dict) -> str:
        items = node.get("items", [])
        if not items:
            return "new Map()"
        pairs = []
        for item in items:
            key_node = item.get("key")
            value_node = item.get("value")

            if isinstance(key_node, dict) and key_node.get("type") == "Array":
                key_items = key_node.get("items", [])
                key_strs = [self.emit_expr(k) for k in key_items]
                key = f"JSON.stringify([{', '.join(key_strs)}])"
                self.uses_tuple_set = True
            elif isinstance(key_node, dict) and key_node.get("type") == "Tuple":
                key_items = key_node.get("items", [])
                key_strs = [self.emit_expr(k) for k in key_items]
                key = f"JSON.stringify([{', '.join(key_strs)}])"
                self.uses_tuple_set = True
            else:
                key = self.emit_expr(key_node)

            value = self.emit_expr(value_node)
            pairs.append(f"[{key}, {value}]")
        return f"new Map([{', '.join(pairs)}])"

    def _emit_get(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        key_node = node.get("key")
        if isinstance(key_node, dict) and key_node.get("type") == "Tuple":
            key_items = key_node.get("items", [])
            key_strs = [self.emit_expr(k) for k in key_items]
            key = f"JSON.stringify([{', '.join(key_strs)}])"
            self.uses_tuple_set = True
        else:
            key = self.emit_expr(key_node)
        return f"{base}.get({key})"

    def _emit_get_default(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        key_node = node.get("key")
        default = self.emit_expr(node.get("default"))
        if isinstance(key_node, dict) and key_node.get("type") == "Tuple":
            key_items = key_node.get("items", [])
            key_strs = [self.emit_expr(k) for k in key_items]
            key = f"JSON.stringify([{', '.join(key_strs)}])"
            self.uses_tuple_set = True
        else:
            key = self.emit_expr(key_node)
        return f"({base}.get({key}) ?? {default})"

    def _emit_keys(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"Array.from({base}.keys())"

    def _emit_tuple(self, node: dict) -> str:
        items = node.get("items", [])
        item_strs = [self.emit_expr(item) for item in items]
        return f"[{', '.join(item_strs)}]"

    def _emit_record(self, node: dict) -> str:
        fields = node.get("fields", [])
        if not fields:
            return "{}"
        field_strs = []
        for field in fields:
            name = field.get("name")
            value = self.emit_expr(field.get("value"))
            field_strs.append(f'"{name}": {value}')
        return "{" + ", ".join(field_strs) + "}"

    def _emit_get_field(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        name = node.get("name")
        return f'{base}["{name}"]'

    def _emit_string_length(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.length"

    def _emit_substring(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        start = self.emit_expr(node.get("start"))
        end = self.emit_expr(node.get("end"))
        return f"{base}.slice({start}, {end})"

    def _emit_char_at(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        return f"{base}[{index}]"

    def _emit_join(self, node: dict) -> str:
        sep = self.emit_expr(node.get("sep"))
        items = self.emit_expr(node.get("items"))
        return f"{items}.map(x => String(x)).join({sep})"

    def _emit_string_split(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        delimiter = self.emit_expr(node.get("delimiter"))
        return f"{base}.split({delimiter})"

    def _emit_string_trim(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.trim()"

    def _emit_string_upper(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.toUpperCase()"

    def _emit_string_lower(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.toLowerCase()"

    def _emit_string_starts_with(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        prefix = self.emit_expr(node.get("prefix"))
        return f"{base}.startsWith({prefix})"

    def _emit_string_ends_with(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        suffix = self.emit_expr(node.get("suffix"))
        return f"{base}.endsWith({suffix})"

    def _emit_string_contains(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        substring = self.emit_expr(node.get("substring"))
        return f"{base}.includes({substring})"

    def _emit_string_replace(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        old = self.emit_expr(node.get("old"))
        new = self.emit_expr(node.get("new"))
        return f"{base}.replaceAll({old}, {new})"

    def _emit_set_expr(self, node: dict) -> str:
        items = node.get("items", [])
        if not items:
            return "new Set()"
        item_strs = []
        for item in items:
            if isinstance(item, dict) and item.get("type") == "Tuple":
                key_items = item.get("items", [])
                key_strs = [self.emit_expr(k) for k in key_items]
                item_strs.append(f"JSON.stringify([{', '.join(key_strs)}])")
                self.uses_tuple_set = True
            else:
                item_strs.append(self.emit_expr(item))
        return f"new Set([{', '.join(item_strs)}])"

    def _emit_set_has(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        value_node = node.get("value")
        if isinstance(value_node, dict) and value_node.get("type") == "Tuple":
            key_items = value_node.get("items", [])
            key_strs = [self.emit_expr(k) for k in key_items]
            value = f"JSON.stringify([{', '.join(key_strs)}])"
            self.uses_tuple_set = True
        else:
            value = self.emit_expr(value_node)
        return f"{base}.has({value})"

    def _emit_set_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.size"

    def _emit_deque_new(self, node: dict) -> str:
        return "[]"

    def _emit_deque_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.length"

    def _emit_heap_new(self, node: dict) -> str:
        self.uses_heap = True
        return "new __CoreILHeap()"

    def _emit_heap_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.size()"

    def _emit_heap_peek(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.peek()"

    def _emit_math(self, node: dict) -> str:
        self.uses_float = True
        op = node.get("op")
        arg = self.emit_expr(node.get("arg"))
        if op in ("floor", "ceil"):
            return f"Math.{op}({arg})"
        elif op == "abs":
            return f"Math.{op}({arg})"
        return f"__float(Math.{op}({arg}))"

    def _emit_math_pow(self, node: dict) -> str:
        self.uses_float = True
        base = self.emit_expr(node.get("base"))
        exponent = self.emit_expr(node.get("exponent"))
        return f"__float(Math.pow({base}, {exponent}))"

    def _emit_math_const(self, node: dict) -> str:
        name = node.get("name")
        if name == "pi":
            return "Math.PI"
        elif name == "e":
            return "Math.E"
        return f"Math.{name.upper()}"

    def _emit_json_parse(self, node: dict) -> str:
        source = self.emit_expr(node.get("source"))
        return f"JSON.parse({source})"

    def _emit_json_stringify(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        pretty = node.get("pretty")
        if pretty:
            pretty_expr = self.emit_expr(pretty)
            return f"JSON.stringify({value}, null, {pretty_expr} ? 2 : undefined)"
        return f"JSON.stringify({value})"

    def _emit_regex_match(self, node: dict) -> str:
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        flags_node = node.get("flags")
        if flags_node:
            self.uses_regex_flags = True
            flags = self.emit_expr(flags_node)
            return f"new RegExp({pattern}, __parseRegexFlags({flags})).test({string})"
        return f"new RegExp({pattern}).test({string})"

    def _emit_regex_find_all(self, node: dict) -> str:
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        flags_node = node.get("flags")
        if flags_node:
            self.uses_regex_flags = True
            flags = self.emit_expr(flags_node)
            return f"(({string}).match(new RegExp({pattern}, __parseRegexFlags({flags}) + 'g')) || [])"
        return f"(({string}).match(new RegExp({pattern}, 'g')) || [])"

    def _emit_regex_replace(self, node: dict) -> str:
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        replacement = self.emit_expr(node.get("replacement"))
        flags_node = node.get("flags")
        if flags_node:
            self.uses_regex_flags = True
            flags = self.emit_expr(flags_node)
            return f"({string}).replace(new RegExp({pattern}, __parseRegexFlags({flags}) + 'g'), {replacement})"
        return f"({string}).replace(new RegExp({pattern}, 'g'), {replacement})"

    def _emit_regex_split(self, node: dict) -> str:
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        flags_node = node.get("flags")
        if flags_node:
            self.uses_regex_flags = True
            flags = self.emit_expr(flags_node)
            return f"({string}).split(new RegExp({pattern}, __parseRegexFlags({flags})))"
        return f"({string}).split(new RegExp({pattern}))"

    def _emit_external_call(self, node: dict) -> str:
        module = node.get("module")
        function = node.get("function")
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        self.external_modules.add(module)
        return f"__external.{module}.{function}({', '.join(arg_strs)})"

    def _emit_method_call(self, node: dict) -> str:
        obj = self.emit_expr(node.get("object"))
        method = node.get("method")
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        return f"{obj}.{method}({', '.join(arg_strs)})"

    def _emit_property_get(self, node: dict) -> str:
        obj = self.emit_expr(node.get("object"))
        prop = node.get("property")
        return f"{obj}.{prop}"

    # ========== Statement Handlers ==========

    def _emit_let(self, node: dict) -> None:
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"let {name} = {value};")

    def _emit_assign(self, node: dict) -> None:
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{name} = {value};")

    def _emit_if(self, node: dict) -> None:
        test = self.emit_expr(node.get("test"))
        self.emit_line(f"if ({test}) {{")
        self.indent_level += 1
        then_body = node.get("then", [])
        if not then_body:
            self.emit_line("// empty")
        else:
            for stmt in then_body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

        else_body = node.get("else")
        if else_body:
            self.emit_line("} else {")
            self.indent_level += 1
            for stmt in else_body:
                self.emit_stmt(stmt)
            self.indent_level -= 1
        self.emit_line("}")

    def _emit_while(self, node: dict) -> None:
        test = self.emit_expr(node.get("test"))
        self.emit_line(f"while ({test}) {{")
        self.indent_level += 1
        body = node.get("body", [])
        if not body:
            self.emit_line("// empty")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1
        self.emit_line("}")

    def _emit_print(self, node: dict) -> None:
        self.uses_print = True
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        self.emit_line(f"__print({', '.join(arg_strs)});")

    def _emit_set_index(self, node: dict) -> None:
        self.uses_index = True
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"__setIdx({base}, {index}, {value});")

    def _emit_set_stmt(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        key_node = node.get("key")
        value = self.emit_expr(node.get("value"))
        if isinstance(key_node, dict) and key_node.get("type") == "Tuple":
            key_items = key_node.get("items", [])
            key_strs = [self.emit_expr(k) for k in key_items]
            key = f"JSON.stringify([{', '.join(key_strs)}])"
            self.uses_tuple_set = True
        else:
            key = self.emit_expr(key_node)
        self.emit_line(f"{base}.set({key}, {value});")

    def _emit_push(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.push({value});")

    def _emit_set_field(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f'{base}["{name}"] = {value};')

    def _emit_set_add(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value_node = node.get("value")
        if isinstance(value_node, dict) and value_node.get("type") == "Tuple":
            key_items = value_node.get("items", [])
            key_strs = [self.emit_expr(k) for k in key_items]
            value = f"JSON.stringify([{', '.join(key_strs)}])"
            self.uses_tuple_set = True
        else:
            value = self.emit_expr(value_node)
        self.emit_line(f"{base}.add({value});")

    def _emit_set_remove(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value_node = node.get("value")
        if isinstance(value_node, dict) and value_node.get("type") == "Tuple":
            key_items = value_node.get("items", [])
            key_strs = [self.emit_expr(k) for k in key_items]
            value = f"JSON.stringify([{', '.join(key_strs)}])"
            self.uses_tuple_set = True
        else:
            value = self.emit_expr(value_node)
        self.emit_line(f"{base}.delete({value});")

    def _emit_push_back(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.push({value});")

    def _emit_push_front(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.unshift({value});")

    def _emit_pop_front(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = {base}.shift();")

    def _emit_pop_back(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = {base}.pop();")

    def _emit_heap_push(self, node: dict) -> None:
        self.uses_heap = True
        base = self.emit_expr(node.get("base"))
        priority = self.emit_expr(node.get("priority"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.push({priority}, {value});")

    def _emit_heap_pop(self, node: dict) -> None:
        self.uses_heap = True
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = {base}.pop();")

    def _emit_func_def(self, node: dict) -> None:
        name = node.get("name")
        params = node.get("params", [])
        self.emit_line(f"function {name}({', '.join(params)}) {{")
        self.indent_level += 1
        body = node.get("body", [])
        if not body:
            self.emit_line("// empty")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1
        self.emit_line("}")

    def _emit_return(self, node: dict) -> None:
        value = node.get("value")
        if value is None:
            self.emit_line("return null;")
        else:
            self.emit_line(f"return {self.emit_expr(value)};")

    def _emit_call_stmt(self, node: dict) -> None:
        name = node.get("name")
        args = node.get("args", [])

        if name == "append":
            if len(args) != 2:
                raise ValueError(f"append expects 2 arguments, got {len(args)}")
            lst = self.emit_expr(args[0])
            value = self.emit_expr(args[1])
            self.emit_line(f"{lst}.push({value});")
            return

        arg_strs = [self.emit_expr(arg) for arg in args]
        self.emit_line(f"{name}({', '.join(arg_strs)});")

    def _emit_break(self, node: dict) -> None:
        self.emit_line("break;")

    def _emit_continue(self, node: dict) -> None:
        self.emit_line("continue;")

    def _emit_for(self, node: dict) -> None:
        var = node.get("var")
        iter_expr = node.get("iter")
        body = node.get("body", [])

        # Handle Range iterator
        if isinstance(iter_expr, dict) and iter_expr.get("type") == "Range":
            from_val = self.emit_expr(iter_expr.get("from"))
            to_val = self.emit_expr(iter_expr.get("to"))
            inclusive = iter_expr.get("inclusive", False)
            cmp_op = "<=" if inclusive else "<"
            self.emit_line(f"for (let {var} = {from_val}; {var} {cmp_op} {to_val}; {var}++) {{")
        else:
            iter_code = self.emit_expr(iter_expr)
            self.emit_line(f"for (const {var} of {iter_code}) {{")

        self.indent_level += 1
        if not body:
            self.emit_line("// empty")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1
        self.emit_line("}")

    def _emit_for_each(self, node: dict) -> None:
        var = node.get("var")
        iter_code = self.emit_expr(node.get("iter"))
        body = node.get("body", [])

        self.emit_line(f"for (const {var} of {iter_code}) {{")
        self.indent_level += 1
        if not body:
            self.emit_line("// empty")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1
        self.emit_line("}")

    def _emit_throw(self, node: dict) -> None:
        message = self.emit_expr(node.get("message"))
        self.emit_line(f"throw new Error({message});")

    def _emit_try_catch(self, node: dict) -> None:
        catch_var = node.get("catch_var")
        body = node.get("body", [])
        catch_body = node.get("catch_body", [])
        finally_body = node.get("finally_body")

        self.emit_line("try {")
        self.indent_level += 1
        if not body:
            self.emit_line("// empty")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

        self.emit_line("} catch (__e) {")
        self.indent_level += 1
        self.emit_line(f"let {catch_var} = (__e instanceof Error) ? __e.message : String(__e);")
        if not catch_body:
            self.emit_line("// empty")
        else:
            for stmt in catch_body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

        if finally_body:
            self.emit_line("} finally {")
            self.indent_level += 1
            for stmt in finally_body:
                self.emit_stmt(stmt)
            self.indent_level -= 1

        self.emit_line("}")


def emit_javascript(doc: dict) -> str:
    """Generate JavaScript code from Core IL document.

    Returns JavaScript source code as a string (ES Module format).
    """
    emitter = JavaScriptEmitter(doc)
    return emitter.emit()

