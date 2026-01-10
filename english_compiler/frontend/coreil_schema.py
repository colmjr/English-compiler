"""Core IL JSON schema for structured output."""

COREIL_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "body"],
    "properties": {
        "version": {"enum": ["coreil-0.1", "coreil-0.2"]},
        "ambiguities": {
            "type": "array",
            "items": {"$ref": "#/definitions/ambiguity"},
        },
        "body": {
            "type": "array",
            "items": {"$ref": "#/definitions/statement"},
        },
    },
    "definitions": {
        "ambiguity": {
            "type": "object",
            "additionalProperties": False,
            "required": ["question", "options", "default"],
            "properties": {
                "question": {"type": "string"},
                "options": {"type": "array", "items": {"type": "string"}},
                "default": {"type": "integer", "minimum": 0},
            },
        },
        "statement": {
            "anyOf": [
                {"$ref": "#/definitions/let_stmt"},
                {"$ref": "#/definitions/assign_stmt"},
                {"$ref": "#/definitions/if_stmt"},
                {"$ref": "#/definitions/while_stmt"},
                {"$ref": "#/definitions/print_stmt"},
                {"$ref": "#/definitions/setindex_stmt"},
            ]
        },
        "let_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "name", "value"],
            "properties": {
                "type": {"const": "Let"},
                "name": {"type": "string"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "assign_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "name", "value"],
            "properties": {
                "type": {"const": "Assign"},
                "name": {"type": "string"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "if_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "test", "then"],
            "properties": {
                "type": {"const": "If"},
                "test": {"$ref": "#/definitions/expr"},
                "then": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/statement"},
                },
                "else": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/statement"},
                },
            },
        },
        "while_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "test", "body"],
            "properties": {
                "type": {"const": "While"},
                "test": {"$ref": "#/definitions/expr"},
                "body": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/statement"},
                },
            },
        },
        "print_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "args"],
            "properties": {
                "type": {"const": "Print"},
                "args": {"type": "array", "items": {"$ref": "#/definitions/expr"}},
            },
        },
        "setindex_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "index", "value"],
            "properties": {
                "type": {"const": "SetIndex"},
                "base": {"$ref": "#/definitions/expr"},
                "index": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "expr": {
            "anyOf": [
                {"$ref": "#/definitions/literal_expr"},
                {"$ref": "#/definitions/var_expr"},
                {"$ref": "#/definitions/binary_expr"},
                {"$ref": "#/definitions/array_expr"},
                {"$ref": "#/definitions/index_expr"},
                {"$ref": "#/definitions/length_expr"},
            ]
        },
        "literal_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "value"],
            "properties": {
                "type": {"const": "Literal"},
                "value": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "number"},
                        {"type": "boolean"},
                        {"type": "array"},
                        {"type": "object"}
                    ]
                },
            },
        },
        "var_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "name"],
            "properties": {
                "type": {"const": "Var"},
                "name": {"type": "string"},
            },
        },
        "binary_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "op", "left", "right"],
            "properties": {
                "type": {"const": "Binary"},
                "op": {
                    "enum": [
                        "+",
                        "-",
                        "*",
                        "/",
                        "%",
                        "==",
                        "!=",
                        "<",
                        "<=",
                        ">",
                        ">=",
                        "and",
                        "or",
                    ]
                },
                "left": {"$ref": "#/definitions/expr"},
                "right": {"$ref": "#/definitions/expr"},
            },
        },
        "array_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "items"],
            "properties": {
                "type": {"const": "Array"},
                "items": {"type": "array", "items": {"$ref": "#/definitions/expr"}},
            },
        },
        "index_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "index"],
            "properties": {
                "type": {"const": "Index"},
                "base": {"$ref": "#/definitions/expr"},
                "index": {"$ref": "#/definitions/expr"},
            },
        },
        "length_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "Length"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
    },
}
