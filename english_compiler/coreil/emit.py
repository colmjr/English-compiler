"""Python code generator for Core IL.

This file implements Core IL v1.2 to Python transpilation.
Core IL v1.2 adds Math operations (Math, MathPow, MathConst).

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
- Imports collections.deque, heapq, and math only when used

Version history:
- v1.2: Added Math, MathPow, MathConst for portable math operations
- v1.1: Added Record, GetField, SetField, Set, Deque operations, String operations, Heap operations
- v1.0: Stable release (frozen)

Backward compatibility: Accepts v0.1 through v1.2 programs.
"""

from __future__ import annotations


def emit_python(doc: dict) -> str:
    """Generate Python code from Core IL document.

    Returns Python source code as a string.
    """
    from english_compiler.coreil.lower import lower_coreil

    # Lower syntax sugar (For/Range) to core constructs (While)
    doc = lower_coreil(doc)

    lines: list[str] = []
    indent_level = 0
    uses_deque = False  # Track if deque is used
    uses_heapq = False  # Track if heapq is used
    uses_math = False   # Track if math is used

    def emit_line(text: str) -> None:
        """Emit a line with current indentation."""
        lines.append("    " * indent_level + text)

    def emit_expr(node: dict) -> str:
        """Generate Python expression code."""
        nonlocal uses_deque, uses_heapq, uses_math

        if not isinstance(node, dict):
            raise ValueError("expected expression node")

        node_type = node.get("type")

        if node_type == "Literal":
            value = node.get("value")
            if isinstance(value, str):
                # Escape quotes in string literals
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escaped}"'
            elif isinstance(value, bool):
                return "True" if value else "False"
            elif value is None:
                return "None"
            else:
                return str(value)

        if node_type == "Var":
            return node.get("name", "")

        if node_type == "Binary":
            op = node.get("op")
            left = emit_expr(node.get("left"))
            right = emit_expr(node.get("right"))
            # Map Core IL operators to Python
            if op == "and":
                return f"({left} and {right})"
            elif op == "or":
                return f"({left} or {right})"
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

        if node_type == "Length":
            base = emit_expr(node.get("base"))
            return f"len({base})"

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
                return f"{d}.get({k}, {default})"

            if name == "entries":
                if len(args) != 1:
                    raise ValueError(f"entries expects 1 argument, got {len(args)}")
                d = emit_expr(args[0])
                return f"list({d}.items())"

            if name == "append":
                if len(args) != 2:
                    raise ValueError(f"append expects 2 arguments, got {len(args)}")
                lst = emit_expr(args[0])
                value = emit_expr(args[1])
                # append as expression: wrap to return None explicitly
                return f"({lst}.append({value}) or None)"

            # Default: emit as regular function call
            arg_strs = [emit_expr(arg) for arg in args]
            return f"{name}({', '.join(arg_strs)})"

        if node_type == "Map":
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
                    key_strs = [emit_expr(k) for k in key_items]
                    # Use trailing comma for single-element tuples
                    if len(key_strs) == 1:
                        key = f"({key_strs[0]},)"
                    else:
                        key = f"({', '.join(key_strs)})"
                else:
                    key = emit_expr(key_node)

                value = emit_expr(value_node)
                pairs.append(f"{key}: {value}")
            return "{" + ", ".join(pairs) + "}"

        if node_type == "Get":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            return f"{base}.get({key})"

        if node_type == "GetDefault":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            default = emit_expr(node.get("default"))
            return f"{base}.get({key}, {default})"

        if node_type == "Keys":
            base = emit_expr(node.get("base"))
            # Return keys in insertion order (deterministic in Python 3.7+)
            # Note: We use insertion order instead of sorted() to handle mixed-type keys
            return f"list({base}.keys())"

        if node_type == "Tuple":
            items = node.get("items", [])
            item_strs = [emit_expr(item) for item in items]
            # Use trailing comma for single-element tuples
            if len(item_strs) == 1:
                return f"({item_strs[0]},)"
            else:
                return f"({', '.join(item_strs)})"

        if node_type == "Record":
            fields = node.get("fields", [])
            if not fields:
                return "{}"
            field_strs = []
            for field in fields:
                name = field.get("name")
                value = emit_expr(field.get("value"))
                # Use quoted field names for dictionary keys
                field_strs.append(f'"{name}": {value}')
            return "{" + ", ".join(field_strs) + "}"

        if node_type == "GetField":
            base = emit_expr(node.get("base"))
            name = node.get("name")
            # Use dictionary access with runtime error on missing field
            return f'{base}["{name}"]'

        if node_type == "StringLength":
            base = emit_expr(node.get("base"))
            return f"len({base})"

        if node_type == "Substring":
            base = emit_expr(node.get("base"))
            start = emit_expr(node.get("start"))
            end = emit_expr(node.get("end"))
            return f"{base}[{start}:{end}]"

        if node_type == "CharAt":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            return f"{base}[{index}]"

        if node_type == "Join":
            sep = emit_expr(node.get("sep"))
            items = emit_expr(node.get("items"))
            # Convert items to strings (matching interpreter behavior)
            return f"{sep}.join(str(x) for x in {items})"

        if node_type == "Set":
            items = node.get("items", [])
            if not items:
                # Empty set must use set() not {}
                return "set()"
            # Use set literal with braces for non-empty sets
            item_exprs = [emit_expr(item) for item in items]
            return "{" + ", ".join(item_exprs) + "}"

        if node_type == "SetHas":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            return f"({value} in {base})"

        if node_type == "SetSize":
            base = emit_expr(node.get("base"))
            return f"len({base})"

        if node_type == "DequeNew":
            uses_deque = True
            return "deque()"

        if node_type == "DequeSize":
            base = emit_expr(node.get("base"))
            return f"len({base})"

        if node_type == "HeapNew":
            uses_heapq = True
            return '{"_heap_items": [], "_heap_counter": 0}'

        if node_type == "HeapSize":
            base = emit_expr(node.get("base"))
            return f'len({base}["_heap_items"])'

        if node_type == "HeapPeek":
            base = emit_expr(node.get("base"))
            return f'{base}["_heap_items"][0][2]'

        if node_type == "Math":
            uses_math = True
            op = node.get("op")
            arg = emit_expr(node.get("arg"))
            if op == "abs":
                return f"abs({arg})"  # abs is a Python builtin
            return f"math.{op}({arg})"

        if node_type == "MathPow":
            uses_math = True
            base = emit_expr(node.get("base"))
            exponent = emit_expr(node.get("exponent"))
            return f"math.pow({base}, {exponent})"

        if node_type == "MathConst":
            uses_math = True
            name = node.get("name")
            return f"math.{name}"

        raise ValueError(f"unknown expression type: {node_type}")

    def emit_stmt(node: dict) -> None:
        """Generate Python statement code."""
        nonlocal indent_level, uses_heapq, uses_math

        if not isinstance(node, dict):
            raise ValueError("expected statement node")

        node_type = node.get("type")

        if node_type == "Let":
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f"{name} = {value}")
            return

        if node_type == "Assign":
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f"{name} = {value}")
            return

        if node_type == "If":
            test = emit_expr(node.get("test"))
            emit_line(f"if {test}:")
            indent_level += 1
            then_body = node.get("then", [])
            if not then_body:
                emit_line("pass")
            else:
                for stmt in then_body:
                    emit_stmt(stmt)
            indent_level -= 1

            else_body = node.get("else")
            if else_body:
                emit_line("else:")
                indent_level += 1
                for stmt in else_body:
                    emit_stmt(stmt)
                indent_level -= 1
            return

        if node_type == "While":
            test = emit_expr(node.get("test"))
            emit_line(f"while {test}:")
            indent_level += 1
            body = node.get("body", [])
            if not body:
                emit_line("pass")
            else:
                for stmt in body:
                    emit_stmt(stmt)
            indent_level -= 1
            return

        if node_type == "Print":
            args = node.get("args", [])
            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"print({', '.join(arg_strs)})")
            return

        if node_type == "SetIndex":
            base = emit_expr(node.get("base"))
            index = emit_expr(node.get("index"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}[{index}] = {value}")
            return

        if node_type == "Set":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}[{key}] = {value}")
            return

        if node_type == "Push":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.append({value})")
            return

        if node_type == "SetField":
            base = emit_expr(node.get("base"))
            name = node.get("name")
            value = emit_expr(node.get("value"))
            emit_line(f'{base}["{name}"] = {value}')
            return

        if node_type == "SetAdd":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.add({value})")
            return

        if node_type == "SetRemove":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            # Use discard for no-op semantics (matching interpreter)
            emit_line(f"{base}.discard({value})")
            return

        if node_type == "PushBack":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.append({value})")
            return

        if node_type == "PushFront":
            base = emit_expr(node.get("base"))
            value = emit_expr(node.get("value"))
            emit_line(f"{base}.appendleft({value})")
            return

        if node_type == "PopFront":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"{target} = {base}.popleft()")
            return

        if node_type == "PopBack":
            base = emit_expr(node.get("base"))
            target = node.get("target")
            emit_line(f"{target} = {base}.pop()")
            return

        if node_type == "HeapPush":
            uses_heapq = True
            base = emit_expr(node.get("base"))
            priority = emit_expr(node.get("priority"))
            value = emit_expr(node.get("value"))
            # Increment counter and push (priority, counter, value) tuple
            emit_line(f'{base}["_heap_counter"] += 1')
            emit_line(f'heapq.heappush({base}["_heap_items"], ({priority}, {base}["_heap_counter"] - 1, {value}))')
            return

        if node_type == "HeapPop":
            uses_heapq = True
            base = emit_expr(node.get("base"))
            target = node.get("target")
            # Pop returns (priority, counter, value), extract value
            emit_line(f'{target} = heapq.heappop({base}["_heap_items"])[2]')
            return

        if node_type == "FuncDef":
            name = node.get("name")
            params = node.get("params", [])
            emit_line(f"def {name}({', '.join(params)}):")
            indent_level += 1
            body = node.get("body", [])
            if not body:
                emit_line("pass")
            else:
                for stmt in body:
                    emit_stmt(stmt)
            indent_level -= 1
            return

        if node_type == "Return":
            value = node.get("value")
            if value is None:
                emit_line("return None")
            else:
                emit_line(f"return {emit_expr(value)}")
            return

        if node_type == "Call":
            # Call can be used as a statement (e.g., print("hello"))
            name = node.get("name")
            args = node.get("args", [])

            # Special-case append as statement (no need for "or None" wrapper)
            if name == "append":
                if len(args) != 2:
                    raise ValueError(f"append expects 2 arguments, got {len(args)}")
                lst = emit_expr(args[0])
                value = emit_expr(args[1])
                emit_line(f"{lst}.append({value})")
                return

            # Default: emit as regular function call statement
            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"{name}({', '.join(arg_strs)})")
            return

        raise ValueError(f"unknown statement type: {node_type}")

    # Generate main code
    body = doc.get("body", [])
    for stmt in body:
        emit_stmt(stmt)

    # Prepend imports if deque, heapq, or math are used
    import_lines = []
    if uses_deque:
        import_lines.append("from collections import deque")
    if uses_heapq:
        import_lines.append("import heapq")
    if uses_math:
        import_lines.append("import math")
    if import_lines:
        for i, line in enumerate(import_lines):
            lines.insert(i, line)
        lines.insert(len(import_lines), "")

    return "\n".join(lines) + "\n"
