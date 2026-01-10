"""Python code generator for Core IL."""

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

    def emit_line(text: str) -> None:
        """Emit a line with current indentation."""
        lines.append("    " * indent_level + text)

    def emit_expr(node: dict) -> str:
        """Generate Python expression code."""
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
            arg_strs = [emit_expr(arg) for arg in args]
            return f"{name}({', '.join(arg_strs)})"

        if node_type == "Map":
            items = node.get("items", [])
            if not items:
                return "{}"
            pairs = []
            for item in items:
                key = emit_expr(item.get("key"))
                value = emit_expr(item.get("value"))
                pairs.append(f"{key}: {value}")
            return "{" + ", ".join(pairs) + "}"

        if node_type == "Get":
            base = emit_expr(node.get("base"))
            key = emit_expr(node.get("key"))
            return f"{base}.get({key})"

        raise ValueError(f"unknown expression type: {node_type}")

    def emit_stmt(node: dict) -> None:
        """Generate Python statement code."""
        nonlocal indent_level

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
            arg_strs = [emit_expr(arg) for arg in args]
            emit_line(f"{name}({', '.join(arg_strs)})")
            return

        raise ValueError(f"unknown statement type: {node_type}")

    # Generate main code
    body = doc.get("body", [])
    for stmt in body:
        emit_stmt(stmt)

    return "\n".join(lines) + "\n"
