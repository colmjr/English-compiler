"""AssemblyScript code generator for Core IL.

This file implements Core IL v1.8 to AssemblyScript transpilation for
WebAssembly compilation. Core IL v1.8 adds TryCatch and Throw for exception handling.

The generated AssemblyScript code:
- Uses the coreil_runtime.ts library for dynamic typing
- Matches interpreter semantics exactly
- Preserves Map insertion order (via OrderedMap)
- Implements short-circuit evaluation
- Record support (mutable named fields)
- Set operations (membership, add, remove, size)
- Deque operations (double-ended queue)
- Heap operations (min-heap priority queue)
- Math operations (sin, cos, tan, sqrt, floor, ceil, abs, log, exp, pow, pi, e)
- JSON operations (JsonParse, JsonStringify)
- Regex operations (RegexMatch, RegexFindAll, RegexReplace, RegexSplit)
- Array slicing (Slice)
- Unary not (Not)
- Break and Continue loop control
- OOP-style method calls and property access (Tier 2)
- TryCatch and Throw exception handling

Version history:
- v1.8: Added Throw and TryCatch exception handling
- v1.7: Added Break and Continue loop control statements
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2, non-portable)
- v1.5: Initial AssemblyScript backend

Backward compatibility: Accepts v0.1 through v1.8 programs.
"""

from __future__ import annotations

from pathlib import Path

from english_compiler.coreil.emit_base import BaseEmitter


def get_runtime_path() -> Path:
    """Return path to the AssemblyScript runtime library."""
    return Path(__file__).parent / "wasm_runtime" / "coreil_runtime.ts"


class AssemblyScriptEmitter(BaseEmitter):
    """AssemblyScript code emitter for Core IL."""

    @property
    def indent_str(self) -> str:
        return "  "

    def _setup_state(self) -> None:
        """Initialize AssemblyScript-specific state."""
        self.uses_math = False
        self.uses_json = False
        self.uses_regex = False
        self.uses_deque = False
        self.uses_heap = False
        self.uses_set = False
        self.uses_map = False
        self.uses_record = False
        self.uses_string_ops = False

    def emit(self) -> str:
        """Generate AssemblyScript code from Core IL document."""
        body = self.doc.get("body", [])
        for stmt in body:
            self.emit_stmt(stmt)

        return self._build_output()

    def _build_output(self) -> str:
        """Build final output with imports and main wrapper."""
        header_lines: list[str] = []

        # Import from runtime
        imports = ["Value", "print", "OrderedMap"]
        if self.uses_set:
            imports.append("OrderedSet")
        if self.uses_deque:
            imports.append("Deque")
        if self.uses_heap:
            imports.append("Heap")
        if self.uses_string_ops:
            imports.extend([
                "stringLength", "substring", "charAt", "join",
                "stringSplit", "stringTrim", "stringUpper", "stringLower",
                "stringStartsWith", "stringEndsWith", "stringContains", "stringReplace"
            ])
        if self.uses_math:
            imports.extend([
                "mathSin", "mathCos", "mathTan", "mathSqrt",
                "mathFloor", "mathCeil", "mathAbs", "mathLog", "mathExp",
                "mathPow", "mathPi", "mathE"
            ])
        if self.uses_json:
            imports.extend(["jsonParse", "jsonStringify"])
        if self.uses_regex:
            imports.extend(["regexMatch", "regexFindAll", "regexReplace", "regexSplit"])

        header_lines.append('import {')
        header_lines.append('  ' + ',\n  '.join(imports))
        header_lines.append('} from "./coreil_runtime";')
        header_lines.append('')

        # Main function wrapper
        header_lines.append('export function main(): void {')

        # Indent all body lines
        body_code = []
        for line in self.lines:
            body_code.append('  ' + line if line else '')

        header_lines.extend(body_code)
        header_lines.append('}')
        header_lines.append('')

        return '\n'.join(header_lines)

    # ========== Expression Handlers ==========

    def _emit_literal(self, node: dict) -> str:
        value = node.get("value")
        if isinstance(value, str):
            escaped = self.escape_string(value)
            return f'Value.fromString("{escaped}")'
        elif isinstance(value, bool):
            return f'Value.fromBool({"true" if value else "false"})'
        elif value is None:
            return "Value.null()"
        elif isinstance(value, float):
            return f"Value.fromFloat({value})"
        else:
            return f"Value.fromInt({value})"

    def _emit_binary(self, node: dict) -> str:
        op = node.get("op")
        left = self.emit_expr(node.get("left"))
        right = self.emit_expr(node.get("right"))

        # Logical operators with short-circuit evaluation
        if op == "and":
            return f"(({left}).isTruthy() ? ({right}) : Value.fromBool(false))"
        elif op == "or":
            # Store left in temp to avoid double evaluation
            return f"((__tmp => __tmp.isTruthy() ? __tmp : ({right}))({left}))"

        # Arithmetic operators
        op_map = {
            "+": "add",
            "-": "sub",
            "*": "mul",
            "/": "div",
            "//": "floorDiv",
            "%": "mod",
        }
        if op in op_map:
            return f"({left}).{op_map[op]}({right})"

        # Comparison operators
        cmp_map = {
            "==": "eq",
            "!=": "ne",
            "<": "lt",
            "<=": "le",
            ">": "gt",
            ">=": "ge",
        }
        if op in cmp_map:
            return f"({left}).{cmp_map[op]}({right})"

        raise ValueError(f"Unknown binary operator: {op}")

    def _emit_array(self, node: dict) -> str:
        items = node.get("items", [])
        if not items:
            return "Value.fromArray([])"
        item_strs = [self.emit_expr(item) for item in items]
        return f"Value.fromArray([{', '.join(item_strs)}])"

    def _emit_index(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        return f"({base}).index({index})"

    def _emit_slice(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        start = self.emit_expr(node.get("start"))
        end = self.emit_expr(node.get("end"))
        return f"({base}).slice({start}, {end})"

    def _emit_not(self, node: dict) -> str:
        arg = self.emit_expr(node.get("arg"))
        return f"({arg}).not()"

    def _emit_length(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"({base}).length()"

    def _emit_call_expr(self, node: dict) -> str:
        name = node.get("name")
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        return f"{name}({', '.join(arg_strs)})"

    def _emit_map(self, node: dict) -> str:
        self.uses_map = True
        items = node.get("items", [])
        if not items:
            return "Value.fromMap(new OrderedMap())"

        lines = ["((): Value => {"]
        lines.append("  const __m = new OrderedMap();")
        for item in items:
            key = self.emit_expr(item.get("key"))
            value = self.emit_expr(item.get("value"))
            lines.append(f"  __m.set({key}, {value});")
        lines.append("  return Value.fromMap(__m);")
        lines.append("})()")
        return "\n".join(lines)

    def _emit_get(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        key = self.emit_expr(node.get("key"))
        return f"({base}).asMap().get({key})"

    def _emit_get_default(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        key = self.emit_expr(node.get("key"))
        default = self.emit_expr(node.get("default"))
        return f"({base}).asMap().getDefault({key}, {default})"

    def _emit_keys(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"Value.fromArray(({base}).asMap().keys())"

    def _emit_tuple(self, node: dict) -> str:
        items = node.get("items", [])
        if not items:
            return "Value.fromTuple([])"
        item_strs = [self.emit_expr(item) for item in items]
        return f"Value.fromTuple([{', '.join(item_strs)}])"

    def _emit_record(self, node: dict) -> str:
        self.uses_record = True
        fields = node.get("fields", [])
        if not fields:
            return "Value.fromRecord(new OrderedMap())"

        lines = ["((): Value => {"]
        lines.append("  const __r = new OrderedMap();")
        for field in fields:
            name = field.get("name")
            value = self.emit_expr(field.get("value"))
            lines.append(f'  __r.set(Value.fromString("{name}"), {value});')
        lines.append("  return Value.fromRecord(__r);")
        lines.append("})()")
        return "\n".join(lines)

    def _emit_get_field(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        name = node.get("name")
        return f'({base}).asRecord().get(Value.fromString("{name}"))'

    def _emit_string_length(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        return f"stringLength({base})"

    def _emit_substring(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        start = self.emit_expr(node.get("start"))
        end = self.emit_expr(node.get("end"))
        return f"substring({base}, {start}, {end})"

    def _emit_char_at(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        return f"charAt({base}, {index})"

    def _emit_join(self, node: dict) -> str:
        self.uses_string_ops = True
        sep = self.emit_expr(node.get("sep"))
        items = self.emit_expr(node.get("items"))
        return f"join({sep}, {items})"

    def _emit_string_split(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        delimiter = self.emit_expr(node.get("delimiter"))
        return f"stringSplit({base}, {delimiter})"

    def _emit_string_trim(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        return f"stringTrim({base})"

    def _emit_string_upper(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        return f"stringUpper({base})"

    def _emit_string_lower(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        return f"stringLower({base})"

    def _emit_string_starts_with(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        prefix = self.emit_expr(node.get("prefix"))
        return f"stringStartsWith({base}, {prefix})"

    def _emit_string_ends_with(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        suffix = self.emit_expr(node.get("suffix"))
        return f"stringEndsWith({base}, {suffix})"

    def _emit_string_contains(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        substring = self.emit_expr(node.get("substring"))
        return f"stringContains({base}, {substring})"

    def _emit_string_replace(self, node: dict) -> str:
        self.uses_string_ops = True
        base = self.emit_expr(node.get("base"))
        old = self.emit_expr(node.get("old"))
        new = self.emit_expr(node.get("new"))
        return f"stringReplace({base}, {old}, {new})"

    def _emit_set_expr(self, node: dict) -> str:
        self.uses_set = True
        items = node.get("items", [])
        if not items:
            return "Value.fromSet(new OrderedSet())"

        lines = ["((): Value => {"]
        lines.append("  const __s = new OrderedSet();")
        for item in items:
            item_expr = self.emit_expr(item)
            lines.append(f"  __s.add({item_expr});")
        lines.append("  return Value.fromSet(__s);")
        lines.append("})()")
        return "\n".join(lines)

    def _emit_set_has(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        return f"Value.fromBool(({base}).asSet().has({value}))"

    def _emit_set_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"Value.fromInt(({base}).asSet().size())"

    def _emit_deque_new(self, node: dict) -> str:
        self.uses_deque = True
        return "Value.fromDeque(new Deque())"

    def _emit_deque_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"Value.fromInt(({base}).asDeque().size())"

    def _emit_heap_new(self, node: dict) -> str:
        self.uses_heap = True
        return "Value.fromHeap(new Heap())"

    def _emit_heap_size(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"Value.fromInt(({base}).asHeap().size())"

    def _emit_heap_peek(self, node: dict) -> str:
        base = self.emit_expr(node.get("base"))
        return f"({base}).asHeap().peek()"

    def _emit_math(self, node: dict) -> str:
        self.uses_math = True
        op = node.get("op")
        arg = self.emit_expr(node.get("arg"))
        op_map = {
            "sin": "mathSin",
            "cos": "mathCos",
            "tan": "mathTan",
            "sqrt": "mathSqrt",
            "floor": "mathFloor",
            "ceil": "mathCeil",
            "abs": "mathAbs",
            "log": "mathLog",
            "exp": "mathExp",
        }
        if op not in op_map:
            raise ValueError(f"Unknown math operation: {op}")
        return f"{op_map[op]}({arg})"

    def _emit_math_pow(self, node: dict) -> str:
        self.uses_math = True
        base = self.emit_expr(node.get("base"))
        exponent = self.emit_expr(node.get("exponent"))
        return f"mathPow({base}, {exponent})"

    def _emit_math_const(self, node: dict) -> str:
        self.uses_math = True
        name = node.get("name")
        if name == "pi":
            return "mathPi()"
        elif name == "e":
            return "mathE()"
        raise ValueError(f"Unknown math constant: {name}")

    def _emit_json_parse(self, node: dict) -> str:
        self.uses_json = True
        source = self.emit_expr(node.get("source"))
        return f"jsonParse({source})"

    def _emit_json_stringify(self, node: dict) -> str:
        self.uses_json = True
        value = self.emit_expr(node.get("value"))
        # Note: pretty printing not yet supported in runtime
        return f"jsonStringify({value})"

    def _emit_regex_match(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        return f"regexMatch({string}, {pattern})"

    def _emit_regex_find_all(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        return f"regexFindAll({string}, {pattern})"

    def _emit_regex_replace(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        replacement = self.emit_expr(node.get("replacement"))
        return f"regexReplace({string}, {pattern}, {replacement})"

    def _emit_regex_split(self, node: dict) -> str:
        self.uses_regex = True
        string = self.emit_expr(node.get("string"))
        pattern = self.emit_expr(node.get("pattern"))
        return f"regexSplit({string}, {pattern})"

    def _emit_external_call(self, node: dict) -> str:
        # ExternalCall is non-portable and errors in WASM
        module = node.get("module")
        function = node.get("function")
        raise ValueError(
            f"ExternalCall({module}.{function}) is not supported in WASM backend"
        )

    def _emit_to_int(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        return f"({value}).toInt()"

    def _emit_to_float(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        return f"({value}).toFloat()"

    def _emit_to_string(self, node: dict) -> str:
        value = self.emit_expr(node.get("value"))
        return f"({value}).toStringConvert()"

    # ========== Statement Handlers ==========

    def _emit_let(self, node: dict) -> None:
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"let {name}: Value = {value};")

    def _emit_assign(self, node: dict) -> None:
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"{name} = {value};")

    def _emit_if(self, node: dict) -> None:
        test = self.emit_expr(node.get("test"))
        self.emit_line(f"if (({test}).isTruthy()) {{")
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
        self.emit_line(f"while (({test}).isTruthy()) {{")
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
        args = node.get("args", [])
        arg_strs = [self.emit_expr(arg) for arg in args]
        self.emit_line(f"print({', '.join(arg_strs)});")

    def _emit_set_index(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        index = self.emit_expr(node.get("index"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).setIndex({index}, {value});")

    def _emit_set_stmt(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        key = self.emit_expr(node.get("key"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).asMap().set({key}, {value});")

    def _emit_push(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).push({value});")

    def _emit_set_field(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        name = node.get("name")
        value = self.emit_expr(node.get("value"))
        self.emit_line(f'({base}).asRecord().set(Value.fromString("{name}"), {value});')

    def _emit_set_add(self, node: dict) -> None:
        self.uses_set = True
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).asSet().add({value});")

    def _emit_set_remove(self, node: dict) -> None:
        self.uses_set = True
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).asSet().delete({value});")

    def _emit_push_back(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).asDeque().pushBack({value});")

    def _emit_push_front(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).asDeque().pushFront({value});")

    def _emit_pop_front(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = ({base}).asDeque().popFront();")

    def _emit_pop_back(self, node: dict) -> None:
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = ({base}).asDeque().popBack();")

    def _emit_heap_push(self, node: dict) -> None:
        self.uses_heap = True
        base = self.emit_expr(node.get("base"))
        priority = self.emit_expr(node.get("priority"))
        value = self.emit_expr(node.get("value"))
        self.emit_line(f"({base}).asHeap().push({priority}, {value});")

    def _emit_heap_pop(self, node: dict) -> None:
        self.uses_heap = True
        base = self.emit_expr(node.get("base"))
        target = node.get("target")
        self.emit_line(f"{target} = ({base}).asHeap().pop();")

    def _emit_func_def(self, node: dict) -> None:
        name = node.get("name")
        params = node.get("params", [])
        param_list = ", ".join(f"{p}: Value" for p in params)
        self.emit_line(f"function {name}({param_list}): Value {{")
        self.indent_level += 1
        body = node.get("body", [])
        if not body:
            self.emit_line("return Value.null();")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1
        self.emit_line("}")

    def _emit_return(self, node: dict) -> None:
        value = node.get("value")
        if value is None:
            self.emit_line("return Value.null();")
        else:
            self.emit_line(f"return {self.emit_expr(value)};")

    def _emit_call_stmt(self, node: dict) -> None:
        name = node.get("name")
        args = node.get("args", [])
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

        if isinstance(iter_expr, dict) and iter_expr.get("type") == "Range":
            from_val = self.emit_expr(iter_expr.get("from"))
            to_val = self.emit_expr(iter_expr.get("to"))
            inclusive = iter_expr.get("inclusive", False)
            cmp_method = "le" if inclusive else "lt"
            self.emit_line(f"for (let {var}: Value = {from_val}; ({var}).{cmp_method}({to_val}).isTruthy(); {var} = ({var}).add(Value.fromInt(1))) {{")
        else:
            iter_code = self.emit_expr(iter_expr)
            self.emit_line(f"for (let __i = 0; __i < ({iter_code}).asArray().length; __i++) {{")
            self.indent_level += 1
            self.emit_line(f"let {var}: Value = ({iter_code}).asArray()[__i];")
            self.indent_level -= 1

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

        self.emit_line(f"for (let __i = 0; __i < ({iter_code}).asArray().length; __i++) {{")
        self.indent_level += 1
        self.emit_line(f"let {var}: Value = ({iter_code}).asArray()[__i];")
        if not body:
            self.emit_line("// empty")
        else:
            for stmt in body:
                self.emit_stmt(stmt)
        self.indent_level -= 1
        self.emit_line("}")

    def _emit_method_call(self, node: dict) -> str:
        raise ValueError("MethodCall is not supported in WASM backend")

    def _emit_property_get(self, node: dict) -> str:
        raise ValueError("PropertyGet is not supported in WASM backend")

    def _emit_throw(self, node: dict) -> None:
        message = self.emit_expr(node.get("message"))
        self.emit_line(f"throw new Error(({message}).asString());")

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
        self.emit_line(f'let {catch_var}: Value = Value.fromString((__e instanceof Error) ? (__e as Error).message : "unknown error");')
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


def emit_assemblyscript(doc: dict) -> str:
    """Generate AssemblyScript code from Core IL document.

    Returns AssemblyScript source code as a string.
    """
    emitter = AssemblyScriptEmitter(doc)
    return emitter.emit()
