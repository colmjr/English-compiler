"""Base class for Core IL code generation backends.

This module provides an abstract base class with dispatch tables for
emitting Core IL to various target languages. Subclasses implement
language-specific formatting while the base class handles traversal.

Version history:
- v1.5: Initial base class extraction from emit.py, emit_javascript.py, emit_cpp.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from english_compiler.coreil.emit_utils import escape_string_literal


class BaseEmitter(ABC):
    """Abstract base class for Core IL code emitters.

    Subclasses must implement:
    - indent_str: The indentation string (e.g., "    " or "  ")
    - Language-specific formatting methods

    The dispatch tables map node types to handler methods, allowing
    O(1) lookup instead of long if/elif chains.
    """

    def __init__(self, doc: dict):
        """Initialize emitter with a Core IL document.

        Args:
            doc: Core IL document (will be lowered automatically)
        """
        from english_compiler.coreil.lower import lower_coreil
        self.doc = lower_coreil(doc)
        self.lines: list[str] = []
        self.indent_level = 0
        self._setup_state()
        self._setup_dispatch_tables()

    def _setup_state(self) -> None:
        """Initialize language-specific state. Override in subclasses."""
        pass

    def _setup_dispatch_tables(self) -> None:
        """Set up expression and statement handler dispatch tables."""
        self.expr_handlers: dict[str, Callable[[dict], str]] = {
            "Literal": self._emit_literal,
            "Var": self._emit_var,
            "Binary": self._emit_binary,
            "Array": self._emit_array,
            "Index": self._emit_index,
            "Slice": self._emit_slice,
            "Not": self._emit_not,
            "Length": self._emit_length,
            "Call": self._emit_call_expr,
            "Map": self._emit_map,
            "Get": self._emit_get,
            "GetDefault": self._emit_get_default,
            "Keys": self._emit_keys,
            "Tuple": self._emit_tuple,
            "Record": self._emit_record,
            "GetField": self._emit_get_field,
            "StringLength": self._emit_string_length,
            "Substring": self._emit_substring,
            "CharAt": self._emit_char_at,
            "Join": self._emit_join,
            "StringSplit": self._emit_string_split,
            "StringTrim": self._emit_string_trim,
            "StringUpper": self._emit_string_upper,
            "StringLower": self._emit_string_lower,
            "StringStartsWith": self._emit_string_starts_with,
            "StringEndsWith": self._emit_string_ends_with,
            "StringContains": self._emit_string_contains,
            "StringReplace": self._emit_string_replace,
            "Set": self._emit_set_expr,
            "SetHas": self._emit_set_has,
            "SetSize": self._emit_set_size,
            "DequeNew": self._emit_deque_new,
            "DequeSize": self._emit_deque_size,
            "HeapNew": self._emit_heap_new,
            "HeapSize": self._emit_heap_size,
            "HeapPeek": self._emit_heap_peek,
            "Math": self._emit_math,
            "MathPow": self._emit_math_pow,
            "MathConst": self._emit_math_const,
            "JsonParse": self._emit_json_parse,
            "JsonStringify": self._emit_json_stringify,
            "RegexMatch": self._emit_regex_match,
            "RegexFindAll": self._emit_regex_find_all,
            "RegexReplace": self._emit_regex_replace,
            "RegexSplit": self._emit_regex_split,
            "ExternalCall": self._emit_external_call,
            "MethodCall": self._emit_method_call,
            "PropertyGet": self._emit_property_get,
        }

        self.stmt_handlers: dict[str, Callable[[dict], None]] = {
            "Let": self._emit_let,
            "Assign": self._emit_assign,
            "If": self._emit_if,
            "While": self._emit_while,
            "Print": self._emit_print,
            "SetIndex": self._emit_set_index,
            "Set": self._emit_set_stmt,
            "Push": self._emit_push,
            "SetField": self._emit_set_field,
            "SetAdd": self._emit_set_add,
            "SetRemove": self._emit_set_remove,
            "PushBack": self._emit_push_back,
            "PushFront": self._emit_push_front,
            "PopFront": self._emit_pop_front,
            "PopBack": self._emit_pop_back,
            "HeapPush": self._emit_heap_push,
            "HeapPop": self._emit_heap_pop,
            "FuncDef": self._emit_func_def,
            "Return": self._emit_return,
            "Call": self._emit_call_stmt,
        }

    @property
    @abstractmethod
    def indent_str(self) -> str:
        """Return the indentation string (e.g., '    ' or '  ')."""
        pass

    def emit_line(self, text: str) -> None:
        """Emit a line with current indentation."""
        self.lines.append(self.indent_str * self.indent_level + text)

    def emit_expr(self, node: dict) -> str:
        """Generate expression code via dispatch table."""
        if not isinstance(node, dict):
            raise ValueError("expected expression node")
        node_type = node.get("type")
        handler = self.expr_handlers.get(node_type)
        if handler is None:
            raise ValueError(f"unknown expression type: {node_type}")
        return handler(node)

    def emit_stmt(self, node: dict) -> None:
        """Generate statement code via dispatch table."""
        if not isinstance(node, dict):
            raise ValueError("expected statement node")
        node_type = node.get("type")
        handler = self.stmt_handlers.get(node_type)
        if handler is None:
            raise ValueError(f"unknown statement type: {node_type}")
        handler(node)

    @abstractmethod
    def emit(self) -> str:
        """Generate code for the entire document. Override in subclasses."""
        pass

    # ========== Expression Handlers (Abstract) ==========

    @abstractmethod
    def _emit_literal(self, node: dict) -> str:
        """Emit a literal value."""
        pass

    def _emit_var(self, node: dict) -> str:
        """Emit a variable reference."""
        return node.get("name", "")

    @abstractmethod
    def _emit_binary(self, node: dict) -> str:
        """Emit a binary operation."""
        pass

    @abstractmethod
    def _emit_array(self, node: dict) -> str:
        """Emit an array literal."""
        pass

    @abstractmethod
    def _emit_index(self, node: dict) -> str:
        """Emit an index operation."""
        pass

    @abstractmethod
    def _emit_slice(self, node: dict) -> str:
        """Emit a slice operation."""
        pass

    @abstractmethod
    def _emit_not(self, node: dict) -> str:
        """Emit a logical not operation."""
        pass

    @abstractmethod
    def _emit_length(self, node: dict) -> str:
        """Emit a length operation."""
        pass

    @abstractmethod
    def _emit_call_expr(self, node: dict) -> str:
        """Emit a function call expression."""
        pass

    @abstractmethod
    def _emit_map(self, node: dict) -> str:
        """Emit a map literal."""
        pass

    @abstractmethod
    def _emit_get(self, node: dict) -> str:
        """Emit a map get operation."""
        pass

    @abstractmethod
    def _emit_get_default(self, node: dict) -> str:
        """Emit a map get with default operation."""
        pass

    @abstractmethod
    def _emit_keys(self, node: dict) -> str:
        """Emit a map keys operation."""
        pass

    @abstractmethod
    def _emit_tuple(self, node: dict) -> str:
        """Emit a tuple literal."""
        pass

    @abstractmethod
    def _emit_record(self, node: dict) -> str:
        """Emit a record literal."""
        pass

    @abstractmethod
    def _emit_get_field(self, node: dict) -> str:
        """Emit a record field access."""
        pass

    @abstractmethod
    def _emit_string_length(self, node: dict) -> str:
        """Emit string length operation."""
        pass

    @abstractmethod
    def _emit_substring(self, node: dict) -> str:
        """Emit substring operation."""
        pass

    @abstractmethod
    def _emit_char_at(self, node: dict) -> str:
        """Emit char at operation."""
        pass

    @abstractmethod
    def _emit_join(self, node: dict) -> str:
        """Emit string join operation."""
        pass

    @abstractmethod
    def _emit_string_split(self, node: dict) -> str:
        """Emit string split operation."""
        pass

    @abstractmethod
    def _emit_string_trim(self, node: dict) -> str:
        """Emit string trim operation."""
        pass

    @abstractmethod
    def _emit_string_upper(self, node: dict) -> str:
        """Emit string upper operation."""
        pass

    @abstractmethod
    def _emit_string_lower(self, node: dict) -> str:
        """Emit string lower operation."""
        pass

    @abstractmethod
    def _emit_string_starts_with(self, node: dict) -> str:
        """Emit string starts with operation."""
        pass

    @abstractmethod
    def _emit_string_ends_with(self, node: dict) -> str:
        """Emit string ends with operation."""
        pass

    @abstractmethod
    def _emit_string_contains(self, node: dict) -> str:
        """Emit string contains operation."""
        pass

    @abstractmethod
    def _emit_string_replace(self, node: dict) -> str:
        """Emit string replace operation."""
        pass

    @abstractmethod
    def _emit_set_expr(self, node: dict) -> str:
        """Emit a set literal expression."""
        pass

    @abstractmethod
    def _emit_set_has(self, node: dict) -> str:
        """Emit set membership test."""
        pass

    @abstractmethod
    def _emit_set_size(self, node: dict) -> str:
        """Emit set size operation."""
        pass

    @abstractmethod
    def _emit_deque_new(self, node: dict) -> str:
        """Emit deque creation."""
        pass

    @abstractmethod
    def _emit_deque_size(self, node: dict) -> str:
        """Emit deque size operation."""
        pass

    @abstractmethod
    def _emit_heap_new(self, node: dict) -> str:
        """Emit heap creation."""
        pass

    @abstractmethod
    def _emit_heap_size(self, node: dict) -> str:
        """Emit heap size operation."""
        pass

    @abstractmethod
    def _emit_heap_peek(self, node: dict) -> str:
        """Emit heap peek operation."""
        pass

    @abstractmethod
    def _emit_math(self, node: dict) -> str:
        """Emit math operation."""
        pass

    @abstractmethod
    def _emit_math_pow(self, node: dict) -> str:
        """Emit math pow operation."""
        pass

    @abstractmethod
    def _emit_math_const(self, node: dict) -> str:
        """Emit math constant."""
        pass

    @abstractmethod
    def _emit_json_parse(self, node: dict) -> str:
        """Emit JSON parse operation."""
        pass

    @abstractmethod
    def _emit_json_stringify(self, node: dict) -> str:
        """Emit JSON stringify operation."""
        pass

    @abstractmethod
    def _emit_regex_match(self, node: dict) -> str:
        """Emit regex match operation."""
        pass

    @abstractmethod
    def _emit_regex_find_all(self, node: dict) -> str:
        """Emit regex find all operation."""
        pass

    @abstractmethod
    def _emit_regex_replace(self, node: dict) -> str:
        """Emit regex replace operation."""
        pass

    @abstractmethod
    def _emit_regex_split(self, node: dict) -> str:
        """Emit regex split operation."""
        pass

    @abstractmethod
    def _emit_external_call(self, node: dict) -> str:
        """Emit external call operation."""
        pass

    @abstractmethod
    def _emit_method_call(self, node: dict) -> str:
        """Emit method call operation (Tier 2, v1.6)."""
        pass

    @abstractmethod
    def _emit_property_get(self, node: dict) -> str:
        """Emit property get operation (Tier 2, v1.6)."""
        pass

    # ========== Statement Handlers (Abstract) ==========

    @abstractmethod
    def _emit_let(self, node: dict) -> None:
        """Emit variable declaration."""
        pass

    @abstractmethod
    def _emit_assign(self, node: dict) -> None:
        """Emit variable assignment."""
        pass

    @abstractmethod
    def _emit_if(self, node: dict) -> None:
        """Emit if statement."""
        pass

    @abstractmethod
    def _emit_while(self, node: dict) -> None:
        """Emit while statement."""
        pass

    @abstractmethod
    def _emit_print(self, node: dict) -> None:
        """Emit print statement."""
        pass

    @abstractmethod
    def _emit_set_index(self, node: dict) -> None:
        """Emit array index assignment."""
        pass

    @abstractmethod
    def _emit_set_stmt(self, node: dict) -> None:
        """Emit map set statement."""
        pass

    @abstractmethod
    def _emit_push(self, node: dict) -> None:
        """Emit array push statement."""
        pass

    @abstractmethod
    def _emit_set_field(self, node: dict) -> None:
        """Emit record field assignment."""
        pass

    @abstractmethod
    def _emit_set_add(self, node: dict) -> None:
        """Emit set add statement."""
        pass

    @abstractmethod
    def _emit_set_remove(self, node: dict) -> None:
        """Emit set remove statement."""
        pass

    @abstractmethod
    def _emit_push_back(self, node: dict) -> None:
        """Emit deque push back statement."""
        pass

    @abstractmethod
    def _emit_push_front(self, node: dict) -> None:
        """Emit deque push front statement."""
        pass

    @abstractmethod
    def _emit_pop_front(self, node: dict) -> None:
        """Emit deque pop front statement."""
        pass

    @abstractmethod
    def _emit_pop_back(self, node: dict) -> None:
        """Emit deque pop back statement."""
        pass

    @abstractmethod
    def _emit_heap_push(self, node: dict) -> None:
        """Emit heap push statement."""
        pass

    @abstractmethod
    def _emit_heap_pop(self, node: dict) -> None:
        """Emit heap pop statement."""
        pass

    @abstractmethod
    def _emit_func_def(self, node: dict) -> None:
        """Emit function definition."""
        pass

    @abstractmethod
    def _emit_return(self, node: dict) -> None:
        """Emit return statement."""
        pass

    @abstractmethod
    def _emit_call_stmt(self, node: dict) -> None:
        """Emit function call statement."""
        pass

    # ========== Utility Methods ==========

    def escape_string(self, value: str) -> str:
        """Escape special characters in a string literal."""
        return escape_string_literal(value)
