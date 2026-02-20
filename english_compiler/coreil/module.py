"""Multi-file module system for Core IL (v1.10.5).

This module implements import resolution for Core IL programs. The key design
is *import flattening*: imported modules' FuncDef nodes are inlined into the
importing document with prefixed names, and all dotted Call references
(e.g., ``utils.add``) are rewritten to use ``__`` separators (``utils__add``).

The result is a flat, import-free Core IL document that existing interpreter
and emitter logic can process without modification.

Usage::

    from english_compiler.coreil.module import resolve_imports

    resolved_doc = resolve_imports(doc, base_dir=Path("examples/"))
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .validate import validate_coreil
from .versions import SUPPORTED_VERSIONS


class CircularImportError(Exception):
    """Raised when a circular import dependency is detected."""


class ModuleNotFoundError(Exception):
    """Raised when an imported module file cannot be found."""


class ModuleCache:
    """Tracks loaded modules and detects circular imports.

    Attributes:
        loaded: Mapping from resolved Path to parsed Core IL document.
        loading: Set of Paths currently being resolved (for cycle detection).
    """

    def __init__(self) -> None:
        self.loaded: dict[Path, dict] = {}
        self.loading: set[Path] = set()


def resolve_module_path(import_path: str, base_dir: Path) -> Path:
    """Resolve an import path string to an absolute ``.coreil.json`` file path.

    The *import_path* is a dotted module name (e.g. ``"utils"`` or
    ``"lib.math_helpers"``).  Dots are converted to directory separators,
    and ``.coreil.json`` is appended.

    Args:
        import_path: Dotted module path from the Import node's ``path`` field.
        base_dir: Directory of the importing file.

    Returns:
        Resolved absolute Path.

    Raises:
        ModuleNotFoundError: If the resolved path does not exist.
    """
    # Convert dots to path separators and add .coreil.json suffix
    relative = import_path.replace(".", "/") + ".coreil.json"
    resolved = (base_dir / relative).resolve()
    if not resolved.is_file():
        raise ModuleNotFoundError(
            f"module '{import_path}' not found: expected {resolved}\n"
            f"Hint: compile the module first (e.g. english-compiler compile {import_path.replace('.', '/')}.txt)"
        )
    return resolved


def load_module_doc(path: Path) -> dict:
    """Load and validate a Core IL module from disk.

    Args:
        path: Absolute path to a ``.coreil.json`` file.

    Returns:
        Parsed Core IL document dict.

    Raises:
        ValueError: If the file cannot be read or fails validation.
    """
    try:
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load module {path}: {exc}") from exc

    if not isinstance(doc, dict):
        raise ValueError(f"module {path} is not a valid Core IL document")

    version = doc.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"module {path} has unsupported version: {version}")

    errors = validate_coreil(doc)
    if errors:
        msgs = "; ".join(f"{e['path']}: {e['message']}" for e in errors[:5])
        raise ValueError(f"module {path} has validation errors: {msgs}")

    return doc


def extract_exports(doc: dict) -> dict[str, dict]:
    """Extract top-level FuncDef nodes from a Core IL document.

    Only FuncDef statements at the top level of the body are considered
    exports. Module-level initialization code (non-FuncDef statements) is
    ignored in the MVP.

    Args:
        doc: A validated Core IL document.

    Returns:
        Mapping from function name to the FuncDef node (deep-copied).
    """
    exports: dict[str, dict] = {}
    for stmt in doc.get("body", []):
        if isinstance(stmt, dict) and stmt.get("type") == "FuncDef":
            name = stmt.get("name")
            if isinstance(name, str) and name:
                exports[name] = copy.deepcopy(stmt)
    return exports


def _rewrite_calls(node: Any, alias: str, func_names: set[str]) -> Any:
    """Recursively rewrite dotted Call names to use ``__`` separator.

    Transforms ``alias.func_name`` to ``alias__func_name`` in all Call nodes
    throughout the AST.

    Args:
        node: Any Core IL AST node (expression, statement, or primitive).
        alias: The module alias (e.g. ``"utils"``).
        func_names: Set of exported function names from that module.

    Returns:
        The node (modified in place for dicts/lists, returned as-is for primitives).
    """
    if isinstance(node, dict):
        # Rewrite Call nodes with dotted names
        if node.get("type") == "Call":
            name = node.get("name", "")
            if "." in name:
                parts = name.split(".", 1)
                if parts[0] == alias and parts[1] in func_names:
                    node["name"] = f"{alias}__{parts[1]}"

        # Recurse into all dict values
        for key, value in node.items():
            _rewrite_calls(value, alias, func_names)

    elif isinstance(node, list):
        for item in node:
            _rewrite_calls(item, alias, func_names)

    return node


def resolve_imports(
    doc: dict,
    base_dir: Path | None = None,
    cache: ModuleCache | None = None,
) -> dict:
    """Resolve all Import nodes in a Core IL document by flattening.

    This is the main entry point for the module system. It:
    1. Finds all Import nodes in the document body.
    2. Loads each imported module (recursively resolving transitive imports).
    3. Inlines imported FuncDef nodes with prefixed names.
    4. Rewrites all dotted Call references to use ``__`` separators.
    5. Returns a flat, import-free Core IL document.

    If the document has no Import nodes, it is returned unchanged (no copy).

    Args:
        doc: The Core IL document to resolve.
        base_dir: Directory to resolve relative imports from.
                  If None, imports are not supported and will raise.
        cache: Optional ModuleCache for tracking loaded modules.

    Returns:
        A new Core IL document with all imports resolved (or the original
        if there were no imports).

    Raises:
        CircularImportError: If circular dependencies are detected.
        ModuleNotFoundError: If an imported module file is missing.
        ValueError: If a module fails to load or validate.
    """
    body = doc.get("body", [])

    # Quick check: are there any Import nodes?
    import_nodes = [
        stmt for stmt in body
        if isinstance(stmt, dict) and stmt.get("type") == "Import"
    ]
    if not import_nodes:
        return doc

    if base_dir is None:
        raise ValueError(
            "Import nodes found but no base_dir provided for module resolution"
        )

    if cache is None:
        cache = ModuleCache()

    # Deep copy the document so we don't mutate the original
    doc = copy.deepcopy(doc)
    body = doc["body"]

    # Collect inlined FuncDefs and track rewrites needed
    inlined_funcs: list[dict] = []
    rewrites: list[tuple[str, set[str]]] = []  # (alias, func_names)

    for stmt in body:
        if not isinstance(stmt, dict) or stmt.get("type") != "Import":
            continue

        import_path = stmt["path"]
        alias = stmt.get("alias") or import_path.rsplit(".", 1)[-1]

        # Resolve and load the module
        module_path = resolve_module_path(import_path, base_dir)

        # Check for circular imports
        if module_path in cache.loading:
            raise CircularImportError(
                f"circular import detected: {import_path} ({module_path})"
            )

        # Use cached module or load fresh
        if module_path in cache.loaded:
            module_doc = cache.loaded[module_path]
        else:
            cache.loading.add(module_path)
            try:
                module_doc = load_module_doc(module_path)
                # Recursively resolve the module's own imports
                module_doc = resolve_imports(
                    module_doc,
                    base_dir=module_path.parent,
                    cache=cache,
                )
                cache.loaded[module_path] = module_doc
            finally:
                cache.loading.discard(module_path)

        # Extract exported functions
        exports = extract_exports(module_doc)
        if not exports:
            continue

        # Prefix function names and inline
        func_names = set(exports.keys())
        for func_name, func_def in exports.items():
            prefixed_name = f"{alias}__{func_name}"
            func_def["name"] = prefixed_name
            # Also rewrite any internal calls within the function body
            # that reference other functions from the same module
            _rewrite_calls(func_def, alias, func_names)
            inlined_funcs.append(func_def)

        rewrites.append((alias, func_names))

    # Remove Import nodes from body
    new_body = [
        stmt for stmt in body
        if not (isinstance(stmt, dict) and stmt.get("type") == "Import")
    ]

    # Prepend inlined functions (before the main program code)
    doc["body"] = inlined_funcs + new_body

    # Rewrite all dotted Call references in the entire document body
    for alias, func_names in rewrites:
        _rewrite_calls(doc["body"], alias, func_names)

    return doc
