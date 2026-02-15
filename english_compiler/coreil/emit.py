"""Python code generator for Core IL.

This file implements Core IL v1.8 to Python transpilation.
Core IL v1.8 adds TryCatch and Throw for exception handling.

The generated Python code:
- Matches interpreter semantics exactly
- Uses standard Python 3.10+ features
- Preserves dictionary insertion order
- Implements short-circuit evaluation naturally
- Record support (mutable named fields)
- Set operations (membership, add, remove, size)
- Deque operations (double-ended queue)
- Heap operations (min-heap priority queue)
- Math operations (sin, cos, tan, sqrt, floor, ceil, abs, log, exp, pow, pi, e)
- JSON operations (parse, stringify)
- Regex operations (match, findall, replace, split)
- Array slicing (Slice)
- Unary not (Not)
- Break and Continue loop control
- OOP-style method calls and property access (Tier 2)
- Imports collections.deque, heapq, math, json, and re only when used

Version history:
- v1.8: Added TryCatch and Throw for exception handling
- v1.7: Added Break and Continue loop control statements
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2, non-portable)
- v1.5: Added Slice for array/list slicing, Not for logical negation
- v1.4: Consolidated Math, JSON, and Regex operations
- v1.3: Added JsonParse, JsonStringify, RegexMatch, RegexFindAll, RegexReplace, RegexSplit
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField, Set, Deque operations, String operations, Heap operations
- v1.0: Stable release (frozen)

Backward compatibility: Accepts v0.1 through v1.8 programs.
"""

from __future__ import annotations

from english_compiler.coreil.emit_base import BaseEmitter


# Map Core IL external module names to Python module names
_EXTERNAL_MODULE_MAP = {
    "fs": "pathlib",  # File system operations
    "http": "urllib.request",  # HTTP requests
    "os": "os",  # OS operations
    "crypto": "hashlib",  # Cryptographic operations
    "time": "time",  # Time operations
}

# Map Core IL external function names to Python function names
_EXTERNAL_FUNCTION_MAP = {
    # time module
    ("time", "now"): "time",        # time.now() -> time.time()
    ("time", "sleep"): "sleep",     # time.sleep() -> time.sleep()
    # os module
    ("os", "env"): "getenv",        # os.env() -> os.getenv()
    ("os", "cwd"): "getcwd",        # os.cwd() -> os.getcwd()
    ("os", "argv"): "sys.argv",     # Special case - needs sys import
    ("os", "exit"): "sys.exit",     # Special case - needs sys import
    # fs module (pathlib)
    ("fs", "readFile"): "Path({}).read_text",   # Needs special handling
    ("fs", "writeFile"): "Path({}).write_text", # Needs special handling
    ("fs", "exists"): "Path({}).exists",        # Needs special handling
    # crypto module (hashlib)
    ("crypto", "hash"): "sha256",   # crypto.hash() -> hashlib.sha256()
}


class PythonEmitter(BaseEmitter):
    """Python code emitter for Core IL."""

    @property
    def indent_str(self) -> str:
        return "    "

    def _setup_state(self) -> None:
        """Initialize Python-specific state."""
        self.uses_deque = False
        self.uses_heapq = False
        self.uses_math = False
        self.uses_json = False
        self.uses_regex = False
        self.external_modules: set[str] = set()

    def emit(self) -> str:
        """Generate Python code from Core IL document."""
        body = self.doc.get("body", [])
        for stmt in body:
            self.emit_stmt(stmt)

        return self._build_output()

    def _build_output(self) -> str:
        """Build final output with imports and helpers."""
        import_lines = []
        if self.uses_deque:
            import_lines.append("from collections import deque")
        if self.uses_heapq:
            import_lines.append("import heapq")
        if self.uses_math:
            import_lines.append("import math")
        if self.uses_json:
            import_lines.append("import json")
        if self.uses_regex:
            import_lines.append("import re")

        # Add imports for external modules (Tier 2)
        for module in sorted(self.external_modules):
            python_module = _EXTERNAL_MODULE_MAP.get(module, module)
            import_lines.append(f"import {python_module}  # External module: {module}")

        # Add helper function for regex flags if regex is used
        helper_lines: list[str] = []
        if self.uses_regex:
            helper_lines.extend([
                "",
                "def _parse_regex_flags(flags_str):",
                "    flags = 0",
                "    if flags_str:",
                "        if 'i' in flags_str:",
                "            flags |= re.IGNORECASE",
                "        if 'm' in flags_str:",
                "            flags |= re.MULTILINE",
                "        if 's' in flags_str:",
                "            flags |= re.DOTALL",
                "    return flags",
            ])

        # Add warning comment for non-portable programs
        if self.external_modules:
            helper_lines.insert(0, "")
            helper_lines.insert(1, "# WARNING: This program uses external calls and is NOT PORTABLE")
            helper_lines.insert(2, f"# Required external modules: {', '.join(sorted(self.external_modules))}")

        if import_lines or helper_lines:
            # Insert imports at the beginning
            for i, line in enumerate(import_lines):
                self.lines.insert(i, line)
            # Insert helper functions after imports
            insert_pos = len(import_lines)
            for i, line in enumerate(helper_lines):
                self.lines.insert(insert_pos + i, line)
            # Add blank line before main code
            self.lines.insert(len(import_lines) + len(helper_lines), "")

        return "\n".join(self.lines) + "\n"

    # ========== Expression Handlers ==========

    def _emit_literal(self, node: dict) -> str:
        value = node.get("value")
        if isinstance(value, str):
            escaped = self.escape_string(value)
            return f'"{escaped}"'
        elif isinstance(value, bool):
            return "True" if value else "False"
        elif value is None:
            return "None"
        else:
            return str(value)

    def _emit_binary(self, node: dict) -> str:
        op = node.get("op")
        left = self.emit_expr(node.get("left"))
        right = self.emit_expr(node.get("right"))
        if op == "and":
            return f"({left} and {right})"
        elif op == "or":
            return f"({left} or {right})"
        else:
            return f"({left} {op} {right})"

    def _emit_array(self, node: dict) -> str:
        items = node.get("items", [])
        item_strs = [self.emit_expr(item) for item in items]
        return f"[{', '.join(item_strs)}]"

    def _emit_index(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        return f"{base}[{index}]"

    def _emit_slice(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        start = self.emit_expr(node.get("start"))
        end = self.emit_expr(node.get("end"))
        return f"{base}[{start}:{end}]"

    def _emit_not(self, node: dict) -> str:
        arg = self.emit_expr(node.get("arg"))
        return f"(not {arg})"

    def _emit_length(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"len({base})"

    def _emit_call_expr(self, node: dict) -> str:
        name = node.get("name")
        args = node.get("args", [])

        # Special-case helper functions to avoid runtime errors
        if name == "get_or_default":
            if len(args) != 3:
                raise ValueError(f"get_or_default expects 3 arguments, got {len(args)}")
            d = self.emit_expr(args[0])
            k = self.emit_expr(args[1])
            default = self.emit_expr(args[2])
            return f"{d}.get({k}, {default})"

        if name == "entries":
            if len(args) != 1:
                raise ValueError(f"entries expects 1 argument, got {len(args)}")
            d = self.emit_expr(args[0])
            return f"list({d}.items())"

        if name == "append":
            if len(args) != 2:
                raise ValueError(f"append expects 2 arguments, got {len(args)}")
            lst = self.emit_expr(args[0])
            value = self.emit_expr(args[1])
            return f"({lst}.append({value}) or None)"

        # Default: emit as regular function call
        arg_strs = [self.emit_expr(arg) for arg in args]
        return f"{name}({', '.join(arg_strs)})"

    def _emit_map(self, node: dict) -> str:
        items = node.get("items", [])
        if not items:
            return "{}"
        pairs = []
        for item in items:
            key_node = item.get("key")
            value_node = item.get("value")

            # v0.4 backward compatibility: convert Array keys to tuples
            if isinstance(key_node, dict) and key_node.get("type") == "Array":
                key_items = key_node.get("items", [])
                key_strs = [self.emit_expr(k) for k in key_items]
                if len(key_strs) == 1:
                    key = f"({key_strs[0]},)"
                else:
                    key = f"({', '.join(key_strs)})"
            else:
                key = self.emit_expr(key_node)

            value = self.emit_expr(value_node)
            pairs.append(f"{key}: {value}")
        return "{" + ", ".join(pairs) + "}"

    def _emit_get(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        key = self.emit_expr(node.get("key"))
        return f"{base}.get({key})"

    def _emit_get_default(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        key = self.emit_expr(node.get("key"))
        default = self.emit_expr(node.get("default"))
        return f"{base}.get({key}, {default})"

    def _emit_keys(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"list({base}.keys())"

    def _emit_tuple(self, node: dict) -> str:
        items = node.get("items", [])
        item_strs = [self.emit_expr(item) for item in items]
        if len(item_strs) == 1:
            return f"({item_strs[0]},)"
        else:
            return f"({', '.join(item_strs)})"

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
        return f"len({base})"

    def _emit_substring(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        start = self.emit_expr(node.get("start"))
        end = self.emit_expr(node.get("end"))
        return f"{base}[{start}:{end}]"

    def _emit_char_at(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        return f"{base}[{index}]"

    def _emit_join(self, node: dict) -> str:
        sep = self.emit_expr(node.get("sep"))
        items = self.emit_expr(node.get("items"))
        return f"{sep}.join(str(x) for x in {items})"

    def _emit_string_split(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        delimiter = self.emit_expr(node.get("delimiter"))
        return f"{base}.split({delimiter})"

    def _emit_string_trim(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.strip()"

    def _emit_string_upper(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.upper()"

    def _emit_string_lower(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"{base}.lower()"

    def _emit_string_starts_with(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        prefix = self.emit_expr(node.get("prefix"))
        return f"{base}.startswith({prefix})"

    def _emit_string_ends_with(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        suffix = self.emit_expr(node.get("suffix"))
        return f"{base}.endswith({suffix})"

    def _emit_string_contains(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        substring = self.emit_expr(node.get("substring"))
        return f"({substring} in {base})"

    def _emit_string_replace(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        old = self.emit_expr(node.get("old"))
        new = self.emit_expr(node.get("new"))
        return f"{base}.replace({old}, {new})"

    def _emit_set_expr(self, node: dict) -> str:
        items = node.get("items", [])
        if not items:
            return "set()"
        item_exprs = [self.emit_expr(item) for item in items]
        return "{" + ", ".join(item_exprs) + "}"

    def _emit_set_has(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        return f"({value} in {base})"

    def _emit_set_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"len({base})"

    def _emit_deque_new(self, node: dict) -> str:
        self.uses_deque = True
        return "deque()"

    def _emit_deque_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"len({base})"

    def _emit_heap_new(self, node: dict) -> str:
        self.uses_heapq = True
        return '{"_heap_items": [], "_heap_counter": 0}'

    def _emit_heap_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f'len({base}["_heap_items"])'

    def _emit_heap_peek(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f'{base}["_heap_items"][0][2]'

    def _emit_math(self, node: dict) -> str:
        self.uses_math = True
        op = node.get("op")
        arg = self.emit_expr(node.get("arg"))
        if op == "abs":
            return f"abs({arg})"  # abs is a Python builtin
        return f"math.{op}({arg})"

    def _emit_math_pow(self, node: dict) -> str:
        self.uses_math = True
        base = self.emit_expr(node.get("base"))
        exponent = self.emit_expr(node.get("exponent"))
        return f"math.pow({base}, {exponent})"

    def _emit_math_const(self, node: dict) -> str:
        self.uses_math = True
        name = node.get("name")
        return f"math.{name}"

    def _emit_json_parse(self, node: dict) -> str:
        self.uses_json = True
        source = self.emit_expr(node.get("source"))
        return f"json.loads({source})"

    def _emit_json_stringify(self, node: dict) -> str:
        self.uses_json = True
        value = self.emit_expr(node.get("value"))
        pretty = node.get("pretty")
        if pretty:
            pretty_expr = self.emit_expr(pretty)
            return f"json.dumps({value}, indent=2 if {pretty_expr} else None, default=lambda o: list(o) if hasattr(o, '__iter__') and not isinstance(o, (str, dict, list)) else None)"
        return f"json.dumps({value}, default=lambda o: list(o) if hasattr(o, '__iter__') and not isinstance(o, (str, dict, list)) else None)"

    def _emit_regex_match(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        flags_node = node.get("flags")
        if flags_node:
            flags = self.emit_expr(flags_node)
            return f"(re.search({pattern}, {string}, _parse_regex_flags({flags})) is not None)"
        return f"(re.search({pattern}, {string}) is not None)"

    def _emit_regex_find_all(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        flags_node = node.get("flags")
        if flags_node:
            flags = self.emit_expr(flags_node)
            return f"re.findall({pattern}, {string}, _parse_regex_flags({flags}))"
        return f"re.findall({pattern}, {string})"

    def _emit_regex_replace(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        replacement = self.emit_expr(node.get("replacement"))
        flags_node = node.get("flags")
        if flags_node:
            flags = self.emit_expr(flags_node)
            return f"re.sub({pattern}, {replacement}, {string}, flags=_parse_regex_flags({flags}))"
        return f"re.sub({pattern}, {replacement}, {string})"

    def _emit_regex_split(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        flags_node = node.get("flags")
        maxsplit_node = node.get("maxsplit")
        maxsplit = "0"
        if maxsplit_node:
            maxsplit = self.emit_expr(maxsplit_node)
        if flags_node:
            flags = self.emit_expr(flags_node)
            return f"re.split({pattern}, {string}, maxsplit={maxsplit}, flags=_parse_regex_flags({flags}))"
        if maxsplit_node:
            return f"re.split({pattern}, {string}, maxsplit={maxsplit})"
        return f"re.split({pattern}, {string})"

    def _emit_external_call(self, node: dict) -> str:
        module = node.get("module")
        function = node.get("function")
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        self.external_modules.add(module)
        python_module = _EXTERNAL_MODULE_MAP.get(module, module)
        python_function = _EXTERNAL_FUNCTION_MAP.get((module, function), function)
        return f"{python_module}.{python_function}({', '.join(arg_strs)})"

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

    def _emit_to_int(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        return f"int({value})"

    def _emit_to_float(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        return f"float({value})"

    def _emit_to_string(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        return f"str({value})"

    # ========== Statement Handlers ==========

    def _emit_let(self, node: dict) -> None:
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{name} = {value}")

    def _emit_assign(self, node: dict) -> None:
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{name} = {value}")

    def _emit_if(self, node: dict) -> None:
        test = self.emit_expr(node.get("test"))
        self.emit_line(f"if {test}:")
        self.indent_level += 1
        then_body = node.get("then", [])
        if not then_body:
            self.emit_line("pass")
        else:
            for stmt in then_body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

        else_body = node.get("else")
        if else_body:
            self.emit_line("else:")
            self.indent_level += 1
            for stmt in else_body:
                self.emit_stmt(stmt)
            self.indent_level -= 1

    def _emit_while(self, node: dict) -> None:
        test = self.emit_expr(node.get("test"))
        self.emit_line(f"while {test}:")
        self.indent_level += 1
        body = node.get("body", [])
        if not body:
            self.emit_line("pass")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

    def _emit_print(self, node: dict) -> None:
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        self.emit_line(f"print({', '.join(arg_strs)})")

    def _emit_set_index(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}[{index}] = {value}")

    def _emit_set_stmt(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        key = self.emit_expr(node.get("key"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}[{key}] = {value}")

    def _emit_push(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.append({value})")

    def _emit_set_field(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f'{base}["{name}"] = {value}')

    def _emit_set_add(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.add({value})")

    def _emit_set_remove(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.discard({value})")

    def _emit_push_back(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.append({value})")

    def _emit_push_front(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{base}.appendleft({value})")

    def _emit_pop_front(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = {base}.popleft()")

    def _emit_pop_back(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = {base}.pop()")

    def _emit_heap_push(self, node: dict) -> None:
        self.uses_heapq = True
        base = self.emit_expr(node.get("base"))
        priority = self.emit_expr(node.get("priority"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f'{base}["_heap_counter"] += 1')
        self.emit_line(f'heapq.heappush({base}["_heap_items"], ({priority}, {base}["_heap_counter"] - 1, {value}))')

    def _emit_heap_pop(self, node: dict) -> None:
        self.uses_heapq = True
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f'{target} = heapq.heappop({base}["_heap_items"])[2]')

    def _emit_func_def(self, node: dict) -> None:
        name = node.get("name")
        params = node.get("params", [])
        self.emit_line(f"def {name}({', '.join(params)}):")
        self.indent_level += 1
        body = node.get("body", [])
        if not body:
            self.emit_line("pass")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

    def _emit_return(self, node: dict) -> None:
        value = node.get("value")
        if value is None:
            self.emit_line("return None")
        else:
            self.emit_line(f"return {self.emit_expr(value)}")

    def _emit_call_stmt(self, node: dict) -> None:
        name = node.get("name")
        args = node.get("args", [])

        # Special-case append as statement
        if name == "append":
            if len(args) != 2:
                raise ValueError(f"append expects 2 arguments, got {len(args)}")
            lst = self.emit_expr(args[0])
            value = self.emit_expr(args[1])
            self.emit_line(f"{lst}.append({value})")
            return

        # Default: emit as regular function call statement
        arg_strs = [self.emit_expr(arg) for arg in args]
        self.emit_line(f"{name}({', '.join(arg_strs)})")

    def _emit_break(self, node: dict) -> None:
        self.emit_line("break")

    def _emit_continue(self, node: dict) -> None:
        self.emit_line("continue")

    def _emit_for(self, node: dict) -> None:
        var = node.get("var")
        iter_expr = node.get("iter")
        body = node.get("body", [])

        # Handle Range iterator
        if isinstance(iter_expr, dict) and iter_expr.get("type") == "Range":
            from_val = self.emit_expr(iter_expr.get("from"))
            to_val = self.emit_expr(iter_expr.get("to"))
            inclusive = iter_expr.get("inclusive", False)
            if inclusive:
                self.emit_line(f"for {var} in range({from_val}, {to_val} + 1):")
            else:
                self.emit_line(f"for {var} in range({from_val}, {to_val}):")
        else:
            iter_code = self.emit_expr(iter_expr)
            self.emit_line(f"for {var} in {iter_code}:")

        self.indent_level += 1
        if not body:
            self.emit_line("pass")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

    def _emit_for_each(self, node: dict) -> None:
        var = node.get("var")
        iter_code = self.emit_expr(node.get("iter"))
        body = node.get("body", [])

        self.emit_line(f"for {var} in {iter_code}:")
        self.indent_level += 1
        if not body:
            self.emit_line("pass")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

    def _emit_throw(self, node: dict) -> None:
        message = self.emit_expr(node.get("message"))
        self.emit_line(f"raise Exception({message})")

    def _emit_try_catch(self, node: dict) -> None:
        catch_var = node.get("catch_var")
        body = node.get("body", [])
        catch_body = node.get("catch_body", [])
        finally_body = node.get("finally_body")

        self.emit_line("try:")
        self.indent_level += 1
        if not body:
            self.emit_line("pass")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

        self.emit_line(f"except Exception as {catch_var}:")
        self.indent_level += 1
        self.emit_line(f"{catch_var} = str({catch_var})")
        if not catch_body:
            self.emit_line("pass")
        else:
            for stmt in catch_body:
                self.emit_stmt(stmt)
        self.indent_level -= 1

        if finally_body:
            self.emit_line("finally:")
            self.indent_level += 1
            for stmt in finally_body:
                self.emit_stmt(stmt)
            self.indent_level -= 1


def emit_python(doc: dict) -> str:
    """Generate Python code from Core IL document.

    Returns Python source code as a string.
    """
    emitter = PythonEmitter(doc)
    return emitter.emit()
