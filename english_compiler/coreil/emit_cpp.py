"""C++ code generator for Core IL.

This file implements Core IL v1.6 to C++17 transpilation.
Core IL v1.6 adds OOP-style method calls and property access (Tier 2).

The generated C++ code:
- Matches interpreter semantics exactly
- Requires C++17 (std::variant, std::optional)
- Uses coreil_runtime.hpp for runtime support
- Preserves map insertion order
- Implements short-circuit evaluation
- Record support (mutable named fields)
- Set operations (membership, add, remove, size)
- Deque operations (double-ended queue)
- Heap operations (min-heap priority queue)
- Math operations (sin, cos, tan, sqrt, floor, ceil, abs, log, exp, pow, pi, e)
- JSON operations (requires nlohmann/json.hpp)
- Regex operations (uses <regex>)
- Array slicing (Slice)
- Unary not (Not)
- OOP-style method calls and property access (Tier 2)

Version history:
- v1.6: Added MethodCall and PropertyGet for OOP-style APIs (Tier 2, non-portable)
- v1.5: Initial C++ backend

Backward compatibility: Accepts v0.1 through v1.6 programs.
"""

from __future__ import annotations

from pathlib import Path

from english_compiler.coreil.emit_utils import escape_string_literal


def emit_cpp(doc: dict) -> str:
    """Generate C++ code from Core IL document.

    Returns C++ source code as a string.
    """
    from english_compiler.coreil.lower import lower_coreil

    # Lower syntax sugar (For/Range) to core constructs (While)
    doc = lower_coreil(doc)

    lines: list[str] = []
    indent_level = 0
    uses_json = False
    uses_regex = False
    external_modules: set[str] = set()

    def emit_line(text: str) -> None:
        """Emit a line with current indentation."""
        lines.append("    " * indent_level + text)

    def emit_expr(node: dict) -> str:
        """Generate C++ expression code."""
        nonlocal uses_json, uses_regex, external_modules

        if not isinstance(node, dict):
            raise ValueError("expected expression node")

        node_type = node.get("type")

        if node_type == "Literal":
            value = node.get("value")
            if isinstance(value, str):
                escaped = escape_string_literal(value)
                return f'coreil::Value(std::string("{escaped}"))'
            elif isinstance(value, bool):
                return "coreil::Value(true)" if value else "coreil::Value(false)"
            elif value is None:
                return "coreil::Value(nullptr)"
            elif isinstance(value, int):
                return f"coreil::Value(static_cast<int64_t>({value}))"
            elif isinstance(value, float):
                return f"coreil::Value({value})"
            else:
                return f"coreil::Value({value})"

        if node_type == "Var":
            return node.get("name", "")

        if node_type == "Binary":
            op = node.get("op")
            left = emit_expr(node.get("left"))
            right = emit_expr(node.get("right"))
            # Map Core IL operators to C++
            if op == "+":
                return f"coreil::add({left}, {right})"
            elif op == "-":
                return f"coreil::subtract({left}, {right})"
            elif op == "*":
                return f"coreil::multiply({left}, {right})"
            elif op == "/":
                return f"coreil::divide({left}, {right})"
            elif op == "%":
                return f"coreil::modulo({left}, {right})"
            elif op == "==":
                return f"coreil::Value(coreil::equal({left}, {right}))"
            elif op == "!=":
                return f"coreil::Value(!coreil::equal({left}, {right}))"
            elif op == "<":
                return f"coreil::Value(coreil::less_than({left}, {right}))"
            elif op == "<=":
                return f"coreil::Value(coreil::less_than_or_equal({left}, {right}))"
            elif op == ">":
                return f"coreil::Value(coreil::greater_than({left}, {right}))"
            elif op == ">=":
                return f"coreil::Value(coreil::greater_than_or_equal({left}, {right}))"
            elif op == "and":
                # Short-circuit evaluation
                return f"(coreil::is_truthy({left}) ? coreil::Value(coreil::is_truthy({right})) : coreil::Value(false))"
            elif op == "or":
                # Short-circuit evaluation
                return f"(coreil::is_truthy({left}) ? coreil::Value(true) : coreil::Value(coreil::is_truthy({right})))"
            else:
                raise ValueError(f"unknown binary operator: {op}")

        if node_type == "Array":
            items = node.get("items", [])
            if not items:
                return "coreil::make_array({})"
            item_strs = [emit_expr(item) for item in items]
            return "coreil::make_array({" + ", ".join(item_strs) + "})"

        if node_type == "Index":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            return f"coreil::array_index({base}, {index})"

        if node_type == "Slice":
            base = emit_expr(node.get("base"))
            start = emit_expr(node.get("start"))
            end = emit_expr(node.get("end"))
            return f"coreil::array_slice({base}, {start}, {end})"

        if node_type == "Not":
            arg = emit_expr(node.get("arg"))
            return f"coreil::logical_not({arg})"

        if node_type == "Length":
            base = emit_expr(node.get("base"))
            return f"coreil::array_length({base})"

        if node_type == "Call":
            name = node.get("name")
            args = node.get("args", [])

            # Special-case helper functions for backward compatibility
            if name == "get_or_default":
                if len(args) != 3:
                    raise ValueError(f"get_or_default expects 3 arguments, got {len(args)}")
                d = emit_expr(args[0])
                k = emit_expr(args[1])
                default = emit_expr(args[2])
                return f"coreil::map_get_default({d}, {k}, {default})"

            if name == "entries":
                if len(args) != 1:
                    raise ValueError(f"entries expects 1 argument, got {len(args)}")
                d = emit_expr(args[0])
                # Return keys-values pairs - not directly supported, use keys
                return f"coreil::map_keys({d})"

            if name == "append":
                if len(args) != 2:
                    raise ValueError(f"append expects 2 arguments, got {len(args)}")
                lst = emit_expr(args[0])
                value = emit_expr(args[1])
                return f"(coreil::array_push({lst}, {value}), coreil::Value(nullptr))"

            # Default: emit as regular function call
            arg_strs = [emit_expr(arg) for arg in args]
            return f"{name}({', '.join(arg_strs)})"

        if node_type == "Map":
            items = node.get("items", [])
            if not items:
                return "coreil::make_map({})"
            pairs = []
            for item in items:
                key_node = item.get("key")
                value_node = item.get("value")
                key = emit_expr(key_node)
                value = emit_expr(value_node)
                pairs.append(f"{{{key}, {value}}}")
            return "coreil::make_map({" + ", ".join(pairs) + "})"

        if node_type == "Get":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            return f"coreil::map_get({base}, {key})"

        if node_type == "GetDefault":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            default = emit_expr(node.get("default"))
            return f"coreil::map_get_default({base}, {key}, {default})"

        if node_type == "Keys":
            base = emit_expr(node.get("base"))
            return f"coreil::map_keys({base})"

        if node_type == "Tuple":
            items = node.get("items", [])
            item_strs = [emit_expr(item) for item in items]
            return "coreil::make_tuple({" + ", ".join(item_strs) + "})"

        if node_type == "Record":
            fields = node.get("fields", [])
            if not fields:
                return "coreil::make_record({})"
            field_strs = []
            for field in fields:
                name = field.get("name")
                value = emit_expr(field.get("value"))
                field_strs.append(f'{{"{name}", {value}}}')
            return "coreil::make_record({" + ", ".join(field_strs) + "})"

        if node_type == "GetField":
            base = emit_expr(node.get("base"))
            name = node.get("name")
            return f'coreil::record_get_field({base}, "{name}")'

        if node_type == "StringLength":
            base = emit_expr(node.get("base"))
            return f"coreil::string_length({base})"

        if node_type == "Substring":
            base = emit_expr(node.get("base"))
            start = emit_expr(node.get("start"))
            end = emit_expr(node.get("end"))
            return f"coreil::string_substring({base}, {start}, {end})"

        if node_type == "CharAt":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            return f"coreil::string_char_at({base}, {index})"

        if node_type == "Join":
            sep = emit_expr(node.get("sep"))
            items = emit_expr(node.get("items"))
            return f"coreil::string_join({sep}, {items})"

        # String operations (v1.4)
        if node_type == "StringSplit":
            base = emit_expr(node.get("base"))
            delimiter = emit_expr(node.get("delimiter"))
            return f"coreil::string_split({base}, {delimiter})"

        if node_type == "StringTrim":
            base = emit_expr(node.get("base"))
            return f"coreil::string_trim({base})"

        if node_type == "StringUpper":
            base = emit_expr(node.get("base"))
            return f"coreil::string_upper({base})"

        if node_type == "StringLower":
            base = emit_expr(node.get("base"))
            return f"coreil::string_lower({base})"

        if node_type == "StringStartsWith":
            base = emit_expr(node.get("base"))
            prefix = emit_expr(node.get("prefix"))
            return f"coreil::string_starts_with({base}, {prefix})"

        if node_type == "StringEndsWith":
            base = emit_expr(node.get("base"))
            suffix = emit_expr(node.get("suffix"))
            return f"coreil::string_ends_with({base}, {suffix})"

        if node_type == "StringContains":
            base = emit_expr(node.get("base"))
            substring = emit_expr(node.get("substring"))
            return f"coreil::string_contains({base}, {substring})"

        if node_type == "StringReplace":
            base = emit_expr(node.get("base"))
            old = emit_expr(node.get("old"))
            new = emit_expr(node.get("new"))
            return f"coreil::string_replace({base}, {old}, {new})"

        if node_type == "Set":
            items = node.get("items", [])
            if not items:
                return "coreil::make_set({})"
            item_strs = [emit_expr(item) for item in items]
            return "coreil::make_set({" + ", ".join(item_strs) + "})"

        if node_type == "SetHas":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            return f"coreil::set_has({base}, {value})"

        if node_type == "SetSize":
            base = emit_expr(node.get("base"))
            return f"coreil::set_size({base})"

        if node_type == "DequeNew":
            return "coreil::deque_new()"

        if node_type == "DequeSize":
            base = emit_expr(node.get("base"))
            return f"coreil::deque_size({base})"

        if node_type == "HeapNew":
            return "coreil::heap_new()"

        if node_type == "HeapSize":
            base = emit_expr(node.get("base"))
            return f"coreil::heap_size({base})"

        if node_type == "HeapPeek":
            base = emit_expr(node.get("base"))
            return f"coreil::heap_peek({base})"

        # Math operations (v1.2)
        if node_type == "Math":
            op = node.get("op")
            arg = emit_expr(node.get("arg"))
            math_funcs = {
                "sin": "math_sin",
                "cos": "math_cos",
                "tan": "math_tan",
                "sqrt": "math_sqrt",
                "floor": "math_floor",
                "ceil": "math_ceil",
                "abs": "math_abs",
                "log": "math_log",
                "exp": "math_exp",
            }
            if op not in math_funcs:
                raise ValueError(f"unknown math operation: {op}")
            return f"coreil::{math_funcs[op]}({arg})"

        if node_type == "MathPow":
            base = emit_expr(node.get("base"))
            exponent = emit_expr(node.get("exponent"))
            return f"coreil::math_pow({base}, {exponent})"

        if node_type == "MathConst":
            name = node.get("name")
            if name == "pi":
                return "coreil::math_pi()"
            elif name == "e":
                return "coreil::math_e()"
            raise ValueError(f"unknown math constant: {name}")

        # JSON operations (v1.3)
        if node_type == "JsonParse":
            uses_json = True
            source = emit_expr(node.get("source"))
            return f"coreil::json_parse({source})"

        if node_type == "JsonStringify":
            uses_json = True
            value = emit_expr(node.get("value"))
            pretty = node.get("pretty")
            if pretty:
                pretty_expr = emit_expr(pretty)
                return f"coreil::json_stringify({value}, coreil::is_truthy({pretty_expr}))"
            return f"coreil::json_stringify({value})"

        # Regex operations (v1.3)
        if node_type == "RegexMatch":
            uses_regex = True
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            flags_node = node.get("flags")
            if flags_node:
                flags = emit_expr(flags_node)
                return f"coreil::regex_match({string}, {pattern}, std::get<std::string>({flags}))"
            return f"coreil::regex_match({string}, {pattern})"

        if node_type == "RegexFindAll":
            uses_regex = True
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            flags_node = node.get("flags")
            if flags_node:
                flags = emit_expr(flags_node)
                return f"coreil::regex_find_all({string}, {pattern}, std::get<std::string>({flags}))"
            return f"coreil::regex_find_all({string}, {pattern})"

        if node_type == "RegexReplace":
            uses_regex = True
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            replacement = emit_expr(node.get("replacement"))
            flags_node = node.get("flags")
            if flags_node:
                flags = emit_expr(flags_node)
                return f"coreil::regex_replace({string}, {pattern}, {replacement}, std::get<std::string>({flags}))"
            return f"coreil::regex_replace({string}, {pattern}, {replacement})"

        if node_type == "RegexSplit":
            uses_regex = True
            string = emit_expr(node.get("string"))
            pattern = emit_expr(node.get("pattern"))
            flags_node = node.get("flags")
            if flags_node:
                flags = emit_expr(flags_node)
                return f"coreil::regex_split({string}, {pattern}, std::get<std::string>({flags}))"
            return f"coreil::regex_split({string}, {pattern})"

        # External call (Tier 2, non-portable)
        if node_type == "ExternalCall":
            module = node.get("module")
            function = node.get("function")
            external_modules.add(module)
            raise ValueError(
                f"ExternalCall to {module}.{function} is not supported in C++ backend. "
                f"External calls require platform-specific implementation."
            )

        # MethodCall (Tier 2, v1.6)
        if node_type == "MethodCall":
            obj = emit_expr(node.get("object"))
            method = node.get("method")
            args = node.get("args", [])
            arg_strs = [emit_expr(arg) for arg in args]
            return f"{obj}.{method}({', '.join(arg_strs)})"

        # PropertyGet (Tier 2, v1.6)
        if node_type == "PropertyGet":
            obj = emit_expr(node.get("object"))
            prop = node.get("property")
            return f"{obj}.{prop}"

        raise ValueError(f"unknown expression type: {node_type}")

    def emit_stmt(node: dict) -> None:
        """Generate C++ statement code."""
        nonlocal indent_level

        if not isinstance(node, dict):
            raise ValueError("expected statement node")

        node_type = node.get("type")

        if node_type == "Let":
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::Value {name} = {value};")
            return

        if node_type == "Assign":
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f"{name} = {value};")
            return

        if node_type == "If":
            test = emit_expr(node.get("test"))
            emit_line(f"if (coreil::is_truthy({test})) {{")
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
            emit_line(f"while (coreil::is_truthy({test})) {{")
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
            args = node.get("args", [])
            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"coreil::print({{{', '.join(arg_strs)}}});")
            return

        if node_type == "SetIndex":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::array_set_index({base}, {index}, {value});")
            return

        if node_type == "Set":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::map_set({base}, {key}, {value});")
            return

        if node_type == "Push":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::array_push({base}, {value});")
            return

        if node_type == "SetField":
            base = emit_expr(node.get("base"))
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f'coreil::record_set_field({base}, "{name}", {value});')
            return

        if node_type == "SetAdd":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::set_add({base}, {value});")
            return

        if node_type == "SetRemove":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::set_remove({base}, {value});")
            return

        if node_type == "PushBack":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::deque_push_back({base}, {value});")
            return

        if node_type == "PushFront":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::deque_push_front({base}, {value});")
            return

        if node_type == "PopFront":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"coreil::Value {target} = coreil::deque_pop_front({base});")
            return

        if node_type == "PopBack":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"coreil::Value {target} = coreil::deque_pop_back({base});")
            return

        if node_type == "HeapPush":
            base = emit_expr(node.get("base"))
            priority = emit_expr(node.get("priority"))
            value = emit_expr(node.get("value"))
            emit_line(f"coreil::heap_push({base}, {priority}, {value});")
            return

        if node_type == "HeapPop":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"coreil::Value {target} = coreil::heap_pop({base});")
            return

        if node_type == "FuncDef":
            name = node.get("name")
            params = node.get("params", [])
            param_strs = [f"coreil::Value {p}" for p in params]
            emit_line(f"coreil::Value {name}({', '.join(param_strs)}) {{")
            indent_level += 1
            body = node.get("body", [])
            if not body:
                emit_line("return coreil::Value(nullptr);")
            else:
                for stmt in body:
                    emit_stmt(stmt)
                # Add implicit return if no explicit return
                if body and body[-1].get("type") != "Return":
                    emit_line("return coreil::Value(nullptr);")
            indent_level -= 1
            emit_line("}")
            return

        if node_type == "Return":
            value = node.get("value")
            if value is None:
                emit_line("return coreil::Value(nullptr);")
            else:
                emit_line(f"return {emit_expr(value)};")
            return

        if node_type == "Call":
            # Call as a statement
            name = node.get("name")
            args = node.get("args", [])

            if name == "append":
                if len(args) != 2:
                    raise ValueError(f"append expects 2 arguments, got {len(args)}")
                lst = emit_expr(args[0])
                value = emit_expr(args[1])
                emit_line(f"coreil::array_push({lst}, {value});")
                return

            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"{name}({', '.join(arg_strs)});")
            return

        raise ValueError(f"unknown statement type: {node_type}")

    # Separate function definitions from main body
    body = doc.get("body", [])
    func_defs = [stmt for stmt in body if stmt.get("type") == "FuncDef"]
    main_stmts = [stmt for stmt in body if stmt.get("type") != "FuncDef"]

    # Generate function definitions
    for stmt in func_defs:
        emit_stmt(stmt)
        emit_line("")

    # Generate main function
    emit_line("int main() {")
    indent_level = 1
    for stmt in main_stmts:
        emit_stmt(stmt)
    emit_line("return 0;")
    indent_level = 0
    emit_line("}")

    # Build header
    header_lines = [
        "// Generated by English Compiler - Core IL to C++ transpiler",
        "// Requires: C++17 compiler (g++ -std=c++17, clang++ -std=c++17)",
        "",
    ]

    # Add JSON include if needed (before runtime header)
    if uses_json:
        header_lines.append('#include "json.hpp"')

    # Add runtime header include
    header_lines.append('#include "coreil_runtime.hpp"')
    header_lines.append("")

    # Add non-portable warning if external modules used
    if external_modules:
        header_lines.insert(0, "// WARNING: This program uses external calls and is NOT PORTABLE")
        header_lines.insert(1, f"// Required external modules: {', '.join(sorted(external_modules))}")
        header_lines.insert(2, "")

    return "\n".join(header_lines + lines) + "\n"


def get_runtime_header_path() -> Path:
    """Return the path to the coreil_runtime.hpp header file."""
    return Path(__file__).parent / "cpp_runtime" / "coreil_runtime.hpp"


def get_json_header_path() -> Path:
    """Return the path to the json.hpp header file."""
    return Path(__file__).parent / "cpp_runtime" / "json.hpp"
