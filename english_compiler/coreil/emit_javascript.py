"""JavaScript code generator for Core IL.

This file implements Core IL v1.5 to JavaScript (ES Modules) transpilation.
Core IL v1.5 adds array/list slicing and unary not operations.

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
- Imports Node.js modules only for Tier 2 ExternalCall operations

Version history:
- v1.5: Added Slice for array/list slicing, Not for logical negation
- v1.4: Initial JavaScript backend (matching Python emit.py)

Backward compatibility: Accepts v0.1 through v1.5 programs.
"""

from __future__ import annotations


# Map Core IL external module names to Node.js imports
_EXTERNAL_MODULE_MAP = {
    "fs": "fs",
    "http": "http",
    "os": "os",
    "crypto": "crypto",
    "time": None,  # Uses Date built-in
}


def emit_javascript(doc: dict) -> str:
    """Generate JavaScript code from Core IL document.

    Returns JavaScript source code as a string (ES Module format).
    """
    from english_compiler.coreil.lower import lower_coreil

    # Lower syntax sugar (For/Range) to core constructs (While)
    doc = lower_coreil(doc)

    lines: list[str] = []
    indent_level = 0
    uses_heap = False
    uses_tuple_set = False  # Track if we need tuple serialization for Set/Map
    uses_regex_flags = False  # Track if we need regex flag helper
    uses_print = False  # Track if we need print helper (for Python-compatible output)
    uses_float = False  # Track if we need float wrapper for Math results
    external_modules: set[str] = set()

    def emit_line(text: str) -> None:
        """Emit a line with current indentation."""
        lines.append("  " * indent_level + text)

    def emit_expr(node: dict) -> str:
        """Generate JavaScript expression code."""
        nonlocal uses_heap, uses_tuple_set, uses_regex_flags, uses_float, external_modules

        if not isinstance(node, dict):
            raise ValueError("expected expression node")

        node_type = node.get("type")

        if node_type == "Literal":
            value = node.get("value")
            if isinstance(value, str):
                # Escape special characters in string literals
                escaped = (value
                    .replace("\\", "\\\\")
                    .replace('"', '\\"')
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t"))
                return f'"{escaped}"'
            elif isinstance(value, bool):
                return "true" if value else "false"
            elif value is None:
                return "null"
            else:
                return str(value)

        if node_type == "Var":
            return node.get("name", "")

        if node_type == "Binary":
            op = node.get("op")
            left = emit_expr(node.get("left"))
            right = emit_expr(node.get("right"))
            # Map Core IL operators to JavaScript
            if op == "and":
                return f"({left} && {right})"
            elif op == "or":
                return f"({left} || {right})"
            elif op == "==":
                return f"({left} === {right})"
            elif op == "!=":
                return f"({left} !== {right})"
            elif op == "//":
                # Integer division: floor(a / b)
                return f"Math.floor({left} / {right})"
            elif op == "%":
                # Python-style modulo (always positive for positive divisor)
                return f"((({left}) % ({right})) + ({right})) % ({right})"
            else:
                return f"({left} {op} {right})"

        if node_type == "Array":
            items = node.get("items", [])
            item_strs = [emit_expr(item) for item in items]
            return f"[{', '.join(item_strs)}]"

        if node_type == "Index":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            return f"{base}[{index}]"

        if node_type == "Slice":
            base = emit_expr(node.get("base"))
            start = emit_expr(node.get("start"))
            end = emit_expr(node.get("end"))
            return f"{base}.slice({start}, {end})"

        if node_type == "Not":
            arg = emit_expr(node.get("arg"))
            return f"(!{arg})"

        if node_type == "Length":
            base = emit_expr(node.get("base"))
            return f"{base}.length"

        if node_type == "Call":
            name = node.get("name")
            args = node.get("args", [])

            # Special-case helper functions to avoid runtime errors
            if name == "get_or_default":
                if len(args) != 3:
                    raise ValueError(f"get_or_default expects 3 arguments, got {len(args)}")
                d = emit_expr(args[0])
                k = emit_expr(args[1])
                default = emit_expr(args[2])
                return f"({d}.get({k}) ?? {default})"

            if name == "entries":
                if len(args) != 1:
                    raise ValueError(f"entries expects 1 argument, got {len(args)}")
                d = emit_expr(args[0])
                return f"Array.from({d}.entries())"

            if name == "append":
                if len(args) != 2:
                    raise ValueError(f"append expects 2 arguments, got {len(args)}")
                lst = emit_expr(args[0])
                value = emit_expr(args[1])
                return f"({lst}.push({value}), null)"

            # Default: emit as regular function call
            arg_strs = [emit_expr(arg) for arg in args]
            return f"{name}({', '.join(arg_strs)})"

        if node_type == "Map":
            items = node.get("items", [])
            if not items:
                return "new Map()"
            pairs = []
            for item in items:
                key_node = item.get("key")
                value_node = item.get("value")

                # v0.4 backward compatibility: convert Array keys to tuples
                if isinstance(key_node, dict) and key_node.get("type") == "Array":
                    key_items = key_node.get("items", [])
                    key_strs = [emit_expr(k) for k in key_items]
                    key = f"JSON.stringify([{', '.join(key_strs)}])"
                    uses_tuple_set = True
                elif isinstance(key_node, dict) and key_node.get("type") == "Tuple":
                    key_items = key_node.get("items", [])
                    key_strs = [emit_expr(k) for k in key_items]
                    key = f"JSON.stringify([{', '.join(key_strs)}])"
                    uses_tuple_set = True
                else:
                    key = emit_expr(key_node)

                value = emit_expr(value_node)
                pairs.append(f"[{key}, {value}]")
            return f"new Map([{', '.join(pairs)}])"

        if node_type == "Get":
            base = emit_expr(node.get("base"))
            key_node = node.get("key")
            # Handle tuple keys
            if isinstance(key_node, dict) and key_node.get("type") == "Tuple":
                key_items = key_node.get("items", [])
                key_strs = [emit_expr(k) for k in key_items]
                key = f"JSON.stringify([{', '.join(key_strs)}])"
                uses_tuple_set = True
            else:
                key = emit_expr(key_node)
            return f"{base}.get({key})"

        if node_type == "GetDefault":
            base = emit_expr(node.get("base"))
            key_node = node.get("key")
            default = emit_expr(node.get("default"))
            # Handle tuple keys
            if isinstance(key_node, dict) and key_node.get("type") == "Tuple":
                key_items = key_node.get("items", [])
                key_strs = [emit_expr(k) for k in key_items]
                key = f"JSON.stringify([{', '.join(key_strs)}])"
                uses_tuple_set = True
            else:
                key = emit_expr(key_node)
            return f"({base}.get({key}) ?? {default})"

        if node_type == "Keys":
            base = emit_expr(node.get("base"))
            return f"Array.from({base}.keys())"

        if node_type == "Tuple":
            # Tuples in JS are represented as arrays (for simple cases)
            # When used as keys, they get JSON-serialized
            items = node.get("items", [])
            item_strs = [emit_expr(item) for item in items]
            return f"[{', '.join(item_strs)}]"

        if node_type == "Record":
            fields = node.get("fields", [])
            if not fields:
                return "{}"
            field_strs = []
            for field in fields:
                name = field.get("name")
                value = emit_expr(field.get("value"))
                field_strs.append(f'"{name}": {value}')
            return "{" + ", ".join(field_strs) + "}"

        if node_type == "GetField":
            base = emit_expr(node.get("base"))
            name = node.get("name")
            return f'{base}["{name}"]'

        if node_type == "StringLength":
            base = emit_expr(node.get("base"))
            return f"{base}.length"

        if node_type == "Substring":
            base = emit_expr(node.get("base"))
            start = emit_expr(node.get("start"))
            end = emit_expr(node.get("end"))
            return f"{base}.slice({start}, {end})"

        if node_type == "CharAt":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            return f"{base}[{index}]"

        if node_type == "Join":
            sep = emit_expr(node.get("sep"))
            items = emit_expr(node.get("items"))
            return f"{items}.map(x => String(x)).join({sep})"

        # String operations (v1.4)
        if node_type == "StringSplit":
            base = emit_expr(node.get("base"))
            delimiter = emit_expr(node.get("delimiter"))
            return f"{base}.split({delimiter})"

        if node_type == "StringTrim":
            base = emit_expr(node.get("base"))
            return f"{base}.trim()"

        if node_type == "StringUpper":
            base = emit_expr(node.get("base"))
            return f"{base}.toUpperCase()"

        if node_type == "StringLower":
            base = emit_expr(node.get("base"))
            return f"{base}.toLowerCase()"

        if node_type == "StringStartsWith":
            base = emit_expr(node.get("base"))
            prefix = emit_expr(node.get("prefix"))
            return f"{base}.startsWith({prefix})"

        if node_type == "StringEndsWith":
            base = emit_expr(node.get("base"))
            suffix = emit_expr(node.get("suffix"))
            return f"{base}.endsWith({suffix})"

        if node_type == "StringContains":
            base = emit_expr(node.get("base"))
            substring = emit_expr(node.get("substring"))
            return f"{base}.includes({substring})"

        if node_type == "StringReplace":
            base = emit_expr(node.get("base"))
            old = emit_expr(node.get("old"))
            new = emit_expr(node.get("new"))
            # replaceAll for all occurrences
            return f"{base}.replaceAll({old}, {new})"

        if node_type == "Set":
            items = node.get("items", [])
            if not items:
                return "new Set()"
            # Check if any items are tuples (need serialization)
            item_strs = []
            for item in items:
                if isinstance(item, dict) and item.get("type") == "Tuple":
                    key_items = item.get("items", [])
                    key_strs = [emit_expr(k) for k in key_items]
                    item_strs.append(f"JSON.stringify([{', '.join(key_strs)}])")
                    uses_tuple_set = True
                else:
                    item_strs.append(emit_expr(item))
            return f"new Set([{', '.join(item_strs)}])"

        if node_type == "SetHas":
            base = emit_expr(node.get("base"))
            value_node = node.get("value")
            if isinstance(value_node, dict) and value_node.get("type") == "Tuple":
                key_items = value_node.get("items", [])
                key_strs = [emit_expr(k) for k in key_items]
                value = f"JSON.stringify([{', '.join(key_strs)}])"
                uses_tuple_set = True
            else:
                value = emit_expr(value_node)
            return f"{base}.has({value})"

        if node_type == "SetSize":
            base = emit_expr(node.get("base"))
            return f"{base}.size"

        if node_type == "DequeNew":
            return "[]"

        if node_type == "DequeSize":
            base = emit_expr(node.get("base"))
            return f"{base}.length"

        if node_type == "HeapNew":
            uses_heap = True
            return "new __CoreILHeap()"

        if node_type == "HeapSize":
            base = emit_expr(node.get("base"))
            return f"{base}.size()"

        if node_type == "HeapPeek":
            base = emit_expr(node.get("base"))
            return f"{base}.peek()"

        # Math operations (v1.2)
        if node_type == "Math":
            uses_float = True
            op = node.get("op")
            arg = emit_expr(node.get("arg"))
            # abs, floor, ceil return integers in Python for integer inputs
            if op in ("floor", "ceil"):
                return f"Math.{op}({arg})"
            elif op == "abs":
                return f"Math.{op}({arg})"
            # Other math ops always return floats in Python
            return f"__float(Math.{op}({arg}))"

        if node_type == "MathPow":
            uses_float = True
            base = emit_expr(node.get("base"))
            exponent = emit_expr(node.get("exponent"))
            return f"__float(Math.pow({base}, {exponent}))"

        if node_type == "MathConst":
            name = node.get("name")
            if name == "pi":
                return "Math.PI"
            elif name == "e":
                return "Math.E"
            return f"Math.{name.upper()}"

        # JSON operations (v1.3)
        if node_type == "JsonParse":
            source = emit_expr(node.get("source"))
            return f"JSON.parse({source})"

        if node_type == "JsonStringify":
            value = emit_expr(node.get("value"))
            pretty = node.get("pretty")
            if pretty:
                pretty_expr = emit_expr(pretty)
                return f"JSON.stringify({value}, null, {pretty_expr} ? 2 : undefined)"
            return f"JSON.stringify({value})"

        # Regex operations (v1.3)
        if node_type == "RegexMatch":
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            flags_node = node.get("flags")
            if flags_node:
                uses_regex_flags = True
                flags = emit_expr(flags_node)
                return f"new RegExp({pattern}, __parseRegexFlags({flags})).test({string})"
            return f"new RegExp({pattern}).test({string})"

        if node_type == "RegexFindAll":
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            flags_node = node.get("flags")
            if flags_node:
                uses_regex_flags = True
                flags = emit_expr(flags_node)
                return f"(({string}).match(new RegExp({pattern}, __parseRegexFlags({flags}) + 'g')) || [])"
            return f"(({string}).match(new RegExp({pattern}, 'g')) || [])"

        if node_type == "RegexReplace":
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            replacement = emit_expr(node.get("replacement"))
            flags_node = node.get("flags")
            if flags_node:
                uses_regex_flags = True
                flags = emit_expr(flags_node)
                return f"({string}).replace(new RegExp({pattern}, __parseRegexFlags({flags}) + 'g'), {replacement})"
            return f"({string}).replace(new RegExp({pattern}, 'g'), {replacement})"

        if node_type == "RegexSplit":
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            flags_node = node.get("flags")
            if flags_node:
                uses_regex_flags = True
                flags = emit_expr(flags_node)
                return f"({string}).split(new RegExp({pattern}, __parseRegexFlags({flags})))"
            return f"({string}).split(new RegExp({pattern}))"

        # External call (Tier 2, non-portable)
        if node_type == "ExternalCall":
            module = node.get("module")
            function = node.get("function")
            args = node.get("args", [])
            arg_strs = [emit_expr(arg) for arg in args]
            external_modules.add(module)
            return f"__external.{module}.{function}({', '.join(arg_strs)})"

        raise ValueError(f"unknown expression type: {node_type}")

    def emit_stmt(node: dict) -> None:
        """Generate JavaScript statement code."""
        nonlocal indent_level, uses_heap, uses_tuple_set, uses_print

        if not isinstance(node, dict):
            raise ValueError("expected statement node")

        node_type = node.get("type")

        if node_type == "Let":
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f"let {name} = {value};")
            return

        if node_type == "Assign":
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f"{name} = {value};")
            return

        if node_type == "If":
            test = emit_expr(node.get("test"))
            emit_line(f"if ({test}) {{")
            indent_level += 1
            then_body = node.get("then", [])
            if not then_body:
                emit_line("// empty")
            else:
                for stmt in then_body:
                    emit_stmt(stmt)
            indent_level -= 1

            else_body = node.get("else")
            if else_body:
                emit_line("} else {")
                indent_level += 1
                for stmt in else_body:
                    emit_stmt(stmt)
                indent_level -= 1
            emit_line("}")
            return

        if node_type == "While":
            test = emit_expr(node.get("test"))
            emit_line(f"while ({test}) {{")
            indent_level += 1
            body = node.get("body", [])
            if not body:
                emit_line("// empty")
            else:
                for stmt in body:
                    emit_stmt(stmt)
            indent_level -= 1
            emit_line("}")
            return

        if node_type == "Print":
            uses_print = True
            args = node.get("args", [])
            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"__print({', '.join(arg_strs)});")
            return

        if node_type == "SetIndex":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}[{index}] = {value};")
            return

        if node_type == "Set":
            base = emit_expr(node.get("base"))
            key_node = node.get("key")
            value = emit_expr(node.get("value"))
            # Handle tuple keys
            if isinstance(key_node, dict) and key_node.get("type") == "Tuple":
                key_items = key_node.get("items", [])
                key_strs = [emit_expr(k) for k in key_items]
                key = f"JSON.stringify([{', '.join(key_strs)}])"
                uses_tuple_set = True
            else:
                key = emit_expr(key_node)
            emit_line(f"{base}.set({key}, {value});")
            return

        if node_type == "Push":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.push({value});")
            return

        if node_type == "SetField":
            base = emit_expr(node.get("base"))
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f'{base}["{name}"] = {value};')
            return

        if node_type == "SetAdd":
            base = emit_expr(node.get("base"))
            value_node = node.get("value")
            if isinstance(value_node, dict) and value_node.get("type") == "Tuple":
                key_items = value_node.get("items", [])
                key_strs = [emit_expr(k) for k in key_items]
                value = f"JSON.stringify([{', '.join(key_strs)}])"
                uses_tuple_set = True
            else:
                value = emit_expr(value_node)
            emit_line(f"{base}.add({value});")
            return

        if node_type == "SetRemove":
            base = emit_expr(node.get("base"))
            value_node = node.get("value")
            if isinstance(value_node, dict) and value_node.get("type") == "Tuple":
                key_items = value_node.get("items", [])
                key_strs = [emit_expr(k) for k in key_items]
                value = f"JSON.stringify([{', '.join(key_strs)}])"
                uses_tuple_set = True
            else:
                value = emit_expr(value_node)
            emit_line(f"{base}.delete({value});")
            return

        if node_type == "PushBack":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.push({value});")
            return

        if node_type == "PushFront":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.unshift({value});")
            return

        if node_type == "PopFront":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"{target} = {base}.shift();")
            return

        if node_type == "PopBack":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"{target} = {base}.pop();")
            return

        if node_type == "HeapPush":
            uses_heap = True
            base = emit_expr(node.get("base"))
            priority = emit_expr(node.get("priority"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.push({priority}, {value});")
            return

        if node_type == "HeapPop":
            uses_heap = True
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"{target} = {base}.pop();")
            return

        if node_type == "FuncDef":
            name = node.get("name")
            params = node.get("params", [])
            emit_line(f"function {name}({', '.join(params)}) {{")
            indent_level += 1
            body = node.get("body", [])
            if not body:
                emit_line("// empty")
            else:
                for stmt in body:
                    emit_stmt(stmt)
            indent_level -= 1
            emit_line("}")
            return

        if node_type == "Return":
            value = node.get("value")
            if value is None:
                emit_line("return null;")
            else:
                emit_line(f"return {emit_expr(value)};")
            return

        if node_type == "Call":
            # Call can be used as a statement
            name = node.get("name")
            args = node.get("args", [])

            # Special-case append as statement
            if name == "append":
                if len(args) != 2:
                    raise ValueError(f"append expects 2 arguments, got {len(args)}")
                lst = emit_expr(args[0])
                value = emit_expr(args[1])
                emit_line(f"{lst}.push({value});")
                return

            # Default: emit as regular function call statement
            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"{name}({', '.join(arg_strs)});")
            return

        raise ValueError(f"unknown statement type: {node_type}")

    # Generate main code
    body = doc.get("body", [])
    for stmt in body:
        emit_stmt(stmt)

    # Prepend imports and helper code if needed
    header_lines: list[str] = []

    # Add external module imports for Tier 2
    if external_modules:
        header_lines.append("// External module imports (Tier 2 - non-portable)")
        for module in sorted(external_modules):
            js_module = _EXTERNAL_MODULE_MAP.get(module)
            if js_module:
                header_lines.append(f"import {module} from '{js_module}';")

        # Add external call dispatcher
        header_lines.append("")
        header_lines.append("// External call dispatcher")
        header_lines.append("const __external = {")
        if "time" in external_modules:
            header_lines.append("  time: {")
            header_lines.append("    now: () => Date.now() / 1000,")
            header_lines.append("    sleep: (ms) => new Promise(r => setTimeout(r, ms * 1000)),")
            header_lines.append("  },")
        if "os" in external_modules:
            header_lines.append("  os: {")
            header_lines.append("    env: (name) => process.env[name] ?? null,")
            header_lines.append("    cwd: () => process.cwd(),")
            header_lines.append("    argv: () => process.argv,")
            header_lines.append("    exit: (code) => process.exit(code),")
            header_lines.append("  },")
        if "fs" in external_modules:
            header_lines.append("  fs: {")
            header_lines.append("    readFile: (path) => fs.readFileSync(path, 'utf-8'),")
            header_lines.append("    writeFile: (path, content) => fs.writeFileSync(path, content, 'utf-8'),")
            header_lines.append("    exists: (path) => fs.existsSync(path),")
            header_lines.append("  },")
        if "crypto" in external_modules:
            header_lines.append("  crypto: {")
            header_lines.append("    hash: (data) => crypto.createHash('sha256').update(data).digest('hex'),")
            header_lines.append("  },")
        if "http" in external_modules:
            header_lines.append("  http: {")
            header_lines.append("    get: (url) => { throw new Error('http.get not implemented'); },")
            header_lines.append("  },")
        header_lines.append("};")

    # Add heap class if needed
    if uses_heap:
        if header_lines:
            header_lines.append("")
        header_lines.append("// Min-heap implementation for Core IL Heap operations")
        header_lines.append("class __CoreILHeap {")
        header_lines.append("  constructor() {")
        header_lines.append("    this._items = [];")
        header_lines.append("    this._counter = 0;")
        header_lines.append("  }")
        header_lines.append("  push(priority, value) {")
        header_lines.append("    const entry = [priority, this._counter++, value];")
        header_lines.append("    this._items.push(entry);")
        header_lines.append("    this._siftUp(this._items.length - 1);")
        header_lines.append("  }")
        header_lines.append("  pop() {")
        header_lines.append("    if (this._items.length === 0) throw new Error('heap is empty');")
        header_lines.append("    const result = this._items[0][2];")
        header_lines.append("    const last = this._items.pop();")
        header_lines.append("    if (this._items.length > 0) {")
        header_lines.append("      this._items[0] = last;")
        header_lines.append("      this._siftDown(0);")
        header_lines.append("    }")
        header_lines.append("    return result;")
        header_lines.append("  }")
        header_lines.append("  peek() {")
        header_lines.append("    if (this._items.length === 0) throw new Error('heap is empty');")
        header_lines.append("    return this._items[0][2];")
        header_lines.append("  }")
        header_lines.append("  size() { return this._items.length; }")
        header_lines.append("  _siftUp(i) {")
        header_lines.append("    while (i > 0) {")
        header_lines.append("      const parent = Math.floor((i - 1) / 2);")
        header_lines.append("      if (this._cmp(this._items[i], this._items[parent]) < 0) {")
        header_lines.append("        [this._items[i], this._items[parent]] = [this._items[parent], this._items[i]];")
        header_lines.append("        i = parent;")
        header_lines.append("      } else break;")
        header_lines.append("    }")
        header_lines.append("  }")
        header_lines.append("  _siftDown(i) {")
        header_lines.append("    const n = this._items.length;")
        header_lines.append("    while (true) {")
        header_lines.append("      let smallest = i;")
        header_lines.append("      const left = 2 * i + 1, right = 2 * i + 2;")
        header_lines.append("      if (left < n && this._cmp(this._items[left], this._items[smallest]) < 0) smallest = left;")
        header_lines.append("      if (right < n && this._cmp(this._items[right], this._items[smallest]) < 0) smallest = right;")
        header_lines.append("      if (smallest === i) break;")
        header_lines.append("      [this._items[i], this._items[smallest]] = [this._items[smallest], this._items[i]];")
        header_lines.append("      i = smallest;")
        header_lines.append("    }")
        header_lines.append("  }")
        header_lines.append("  _cmp(a, b) {")
        header_lines.append("    if (a[0] !== b[0]) return a[0] - b[0];")
        header_lines.append("    return a[1] - b[1];")
        header_lines.append("  }")
        header_lines.append("}")

    # Add regex flags helper if needed
    if uses_regex_flags:
        if header_lines:
            header_lines.append("")
        header_lines.append("// Regex flags parser")
        header_lines.append("function __parseRegexFlags(flags) {")
        header_lines.append("  let result = '';")
        header_lines.append("  if (flags && flags.includes('i')) result += 'i';")
        header_lines.append("  if (flags && flags.includes('m')) result += 'm';")
        header_lines.append("  if (flags && flags.includes('s')) result += 's';")
        header_lines.append("  return result;")
        header_lines.append("}")

    # Add float wrapper for Math operations (ensures Python-compatible float output)
    if uses_float:
        if header_lines:
            header_lines.append("")
        header_lines.append("// Float wrapper to preserve Python-like float formatting")
        header_lines.append("class __Float {")
        header_lines.append("  constructor(v) { this.value = v; }")
        header_lines.append("  valueOf() { return this.value; }")
        header_lines.append("  toString() {")
        header_lines.append("    if (Number.isInteger(this.value)) return this.value + '.0';")
        header_lines.append("    return String(this.value);")
        header_lines.append("  }")
        header_lines.append("}")
        header_lines.append("function __float(v) { return new __Float(v); }")

    # Add print helper for Python-compatible output format
    if uses_print:
        if header_lines:
            header_lines.append("")
        header_lines.append("// Print helper for Python-compatible output")
        header_lines.append("function __format(v) {")
        header_lines.append("  if (v === true) return 'True';")
        header_lines.append("  if (v === false) return 'False';")
        header_lines.append("  if (v === null) return 'None';")
        if uses_float:
            header_lines.append("  if (v instanceof __Float) return v.toString();")
        header_lines.append("  if (Array.isArray(v)) return '[' + v.map(__format).join(', ') + ']';")
        header_lines.append("  return v;")
        header_lines.append("}")
        header_lines.append("function __print(...args) {")
        header_lines.append("  console.log(args.map(__format).join(' '));")
        header_lines.append("}")

    # Add warning comment for non-portable programs
    if external_modules:
        warning = [
            "// WARNING: This program uses external calls and is NOT PORTABLE",
            f"// Required external modules: {', '.join(sorted(external_modules))}",
        ]
        header_lines = warning + [""] + header_lines

    if header_lines:
        header_lines.append("")
        result = "\n".join(header_lines) + "\n".join(lines) + "\n"
    else:
        result = "\n".join(lines) + "\n"

    return result
