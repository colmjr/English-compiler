"""Core IL JSON schema for structured output.

This schema defines Core IL v1.1 structure for LLM frontends.
Core IL v1.1 adds Record, Set, String operations, Deque support, and Heap support.

Version history:
- v1.1: Added Record, GetField, SetField, Set, Deque operations, String operations, Heap operations
- v1.0: Stable release (frozen)

Backward compatibility: Schema accepts v0.1 through v1.1 for validation,
but LLMs should generate v1.1 programs.
"""

COREIL_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "body"],
    "properties": {
        "version": {"enum": ["coreil-0.1", "coreil-0.2", "coreil-0.3", "coreil-0.4", "coreil-0.5", "coreil-1.0", "coreil-1.1"]},
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
                {"$ref": "#/definitions/set_stmt"},
                {"$ref": "#/definitions/funcdef_stmt"},
                {"$ref": "#/definitions/return_stmt"},
                {"$ref": "#/definitions/for_stmt"},
                {"$ref": "#/definitions/foreach_stmt"},
                {"$ref": "#/definitions/push_stmt"},
                {"$ref": "#/definitions/setfield_stmt"},
                {"$ref": "#/definitions/setadd_stmt"},
                {"$ref": "#/definitions/setremove_stmt"},
                {"$ref": "#/definitions/pushback_stmt"},
                {"$ref": "#/definitions/pushfront_stmt"},
                {"$ref": "#/definitions/popfront_stmt"},
                {"$ref": "#/definitions/popback_stmt"},
                {"$ref": "#/definitions/heappush_stmt"},
                {"$ref": "#/definitions/heappop_stmt"},
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
        "funcdef_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "name", "params", "body"],
            "properties": {
                "type": {"const": "FuncDef"},
                "name": {"type": "string"},
                "params": {"type": "array", "items": {"type": "string"}},
                "body": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/statement"},
                },
            },
        },
        "return_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type"],
            "properties": {
                "type": {"const": "Return"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "for_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "var", "iter", "body"],
            "properties": {
                "type": {"const": "For"},
                "var": {"type": "string"},
                "iter": {"$ref": "#/definitions/expr"},
                "body": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/statement"},
                },
            },
        },
        "foreach_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "var", "iter", "body"],
            "properties": {
                "type": {"const": "ForEach"},
                "var": {"type": "string"},
                "iter": {"$ref": "#/definitions/expr"},
                "body": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/statement"},
                },
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
                {"$ref": "#/definitions/call_expr"},
                {"$ref": "#/definitions/range_expr"},
                {"$ref": "#/definitions/map_expr"},
                {"$ref": "#/definitions/get_expr"},
                {"$ref": "#/definitions/getdefault_expr"},
                {"$ref": "#/definitions/keys_expr"},
                {"$ref": "#/definitions/tuple_expr"},
                {"$ref": "#/definitions/record_expr"},
                {"$ref": "#/definitions/getfield_expr"},
                {"$ref": "#/definitions/stringlength_expr"},
                {"$ref": "#/definitions/substring_expr"},
                {"$ref": "#/definitions/charat_expr"},
                {"$ref": "#/definitions/join_expr"},
                {"$ref": "#/definitions/set_expr"},
                {"$ref": "#/definitions/sethas_expr"},
                {"$ref": "#/definitions/setsize_expr"},
                {"$ref": "#/definitions/dequenew_expr"},
                {"$ref": "#/definitions/dequesize_expr"},
                {"$ref": "#/definitions/heapnew_expr"},
                {"$ref": "#/definitions/heapsize_expr"},
                {"$ref": "#/definitions/heappeek_expr"},
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
                        {"type": "object"},
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
        "call_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "name", "args"],
            "properties": {
                "type": {"const": "Call"},
                "name": {"type": "string"},
                "args": {"type": "array", "items": {"$ref": "#/definitions/expr"}},
            },
        },
        "range_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "from", "to"],
            "properties": {
                "type": {"const": "Range"},
                "from": {"$ref": "#/definitions/expr"},
                "to": {"$ref": "#/definitions/expr"},
                "inclusive": {"type": "boolean"},
            },
        },
        "set_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "key", "value"],
            "properties": {
                "type": {"const": "Set"},
                "base": {"$ref": "#/definitions/expr"},
                "key": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "map_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "items"],
            "properties": {
                "type": {"const": "Map"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["key", "value"],
                        "properties": {
                            "key": {"$ref": "#/definitions/expr"},
                            "value": {"$ref": "#/definitions/expr"},
                        },
                    },
                },
            },
        },
        "get_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "key"],
            "properties": {
                "type": {"const": "Get"},
                "base": {"$ref": "#/definitions/expr"},
                "key": {"$ref": "#/definitions/expr"},
            },
        },
        "getdefault_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "key", "default"],
            "properties": {
                "type": {"const": "GetDefault"},
                "base": {"$ref": "#/definitions/expr"},
                "key": {"$ref": "#/definitions/expr"},
                "default": {"$ref": "#/definitions/expr"},
            },
        },
        "keys_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "Keys"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
        "tuple_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "items"],
            "properties": {
                "type": {"const": "Tuple"},
                "items": {"type": "array", "items": {"$ref": "#/definitions/expr"}},
            },
        },
        "push_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "value"],
            "properties": {
                "type": {"const": "Push"},
                "base": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "record_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "fields"],
            "properties": {
                "type": {"const": "Record"},
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "value"],
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"$ref": "#/definitions/expr"},
                        },
                    },
                },
            },
        },
        "getfield_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "name"],
            "properties": {
                "type": {"const": "GetField"},
                "base": {"$ref": "#/definitions/expr"},
                "name": {"type": "string"},
            },
        },
        "setfield_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "name", "value"],
            "properties": {
                "type": {"const": "SetField"},
                "base": {"$ref": "#/definitions/expr"},
                "name": {"type": "string"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "stringlength_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "StringLength"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
        "substring_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "start", "end"],
            "properties": {
                "type": {"const": "Substring"},
                "base": {"$ref": "#/definitions/expr"},
                "start": {"$ref": "#/definitions/expr"},
                "end": {"$ref": "#/definitions/expr"},
            },
        },
        "charat_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "index"],
            "properties": {
                "type": {"const": "CharAt"},
                "base": {"$ref": "#/definitions/expr"},
                "index": {"$ref": "#/definitions/expr"},
            },
        },
        "join_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "sep", "items"],
            "properties": {
                "type": {"const": "Join"},
                "sep": {"$ref": "#/definitions/expr"},
                "items": {"$ref": "#/definitions/expr"},
            },
        },
        "set_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "items"],
            "properties": {
                "type": {"const": "Set"},
                "items": {"type": "array", "items": {"$ref": "#/definitions/expr"}},
            },
        },
        "sethas_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "value"],
            "properties": {
                "type": {"const": "SetHas"},
                "base": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "setsize_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "SetSize"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
        "setadd_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "value"],
            "properties": {
                "type": {"const": "SetAdd"},
                "base": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "setremove_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "value"],
            "properties": {
                "type": {"const": "SetRemove"},
                "base": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "dequenew_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type"],
            "properties": {
                "type": {"const": "DequeNew"},
            },
        },
        "dequesize_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "DequeSize"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
        "pushback_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "value"],
            "properties": {
                "type": {"const": "PushBack"},
                "base": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "pushfront_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "value"],
            "properties": {
                "type": {"const": "PushFront"},
                "base": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "popfront_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "target"],
            "properties": {
                "type": {"const": "PopFront"},
                "base": {"$ref": "#/definitions/expr"},
                "target": {"type": "string"},
            },
        },
        "popback_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "target"],
            "properties": {
                "type": {"const": "PopBack"},
                "base": {"$ref": "#/definitions/expr"},
                "target": {"type": "string"},
            },
        },
        "heapnew_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type"],
            "properties": {
                "type": {"const": "HeapNew"},
            },
        },
        "heapsize_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "HeapSize"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
        "heappeek_expr": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base"],
            "properties": {
                "type": {"const": "HeapPeek"},
                "base": {"$ref": "#/definitions/expr"},
            },
        },
        "heappush_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "priority", "value"],
            "properties": {
                "type": {"const": "HeapPush"},
                "base": {"$ref": "#/definitions/expr"},
                "priority": {"$ref": "#/definitions/expr"},
                "value": {"$ref": "#/definitions/expr"},
            },
        },
        "heappop_stmt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["type", "base", "target"],
            "properties": {
                "type": {"const": "HeapPop"},
                "base": {"$ref": "#/definitions/expr"},
                "target": {"type": "string"},
            },
        },
    },
}
