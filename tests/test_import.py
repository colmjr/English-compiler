"""Tests for the multi-file module system (Core IL v1.10.5).

Tests cover:
- Validation: Import node validation rules
- Module resolution: resolve_module_path finds files, errors on missing
- Import flattening: resolve_imports renames functions & calls correctly
- Transitive imports: A imports B which imports C
- Circular import detection
- Interpreter E2E: two fixture files, verify output
- Python parity: interpreter output == Python backend output
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from english_compiler.coreil.interp import run_coreil
from english_compiler.coreil.module import (
    CircularImportError,
    ModuleCache,
    ModuleNotFoundError,
    extract_exports,
    resolve_imports,
    resolve_module_path,
)
from english_compiler.coreil.validate import validate_coreil
from english_compiler.coreil.versions import COREIL_VERSION


def _make_doc(body: list[dict], version: str = COREIL_VERSION) -> dict:
    return {"version": version, "body": body}


def _write_module(directory: Path, name: str, body: list[dict]) -> Path:
    """Write a Core IL module to a .coreil.json file."""
    doc = _make_doc(body)
    path = directory / f"{name}.coreil.json"
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return path


class TestImportValidation(unittest.TestCase):
    """Test that the validator accepts/rejects Import nodes correctly."""

    def test_valid_import(self):
        doc = _make_doc([
            {"type": "Import", "path": "utils"},
        ])
        errors = validate_coreil(doc)
        self.assertEqual(errors, [])

    def test_valid_import_with_alias(self):
        doc = _make_doc([
            {"type": "Import", "path": "math_utils", "alias": "mu"},
        ])
        errors = validate_coreil(doc)
        self.assertEqual(errors, [])

    def test_import_missing_path(self):
        doc = _make_doc([
            {"type": "Import"},
        ])
        errors = validate_coreil(doc)
        self.assertTrue(any("path" in e["path"] for e in errors))

    def test_import_empty_path(self):
        doc = _make_doc([
            {"type": "Import", "path": ""},
        ])
        errors = validate_coreil(doc)
        self.assertTrue(any("path" in e["path"] for e in errors))

    def test_import_invalid_alias(self):
        doc = _make_doc([
            {"type": "Import", "path": "utils", "alias": ""},
        ])
        errors = validate_coreil(doc)
        self.assertTrue(any("alias" in e["path"] for e in errors))

    def test_import_inside_function_rejected(self):
        doc = _make_doc([
            {
                "type": "FuncDef", "name": "foo", "params": [],
                "body": [
                    {"type": "Import", "path": "utils"},
                ],
            },
        ])
        errors = validate_coreil(doc)
        self.assertTrue(any("top level" in e["message"] for e in errors))


class TestResolveModulePath(unittest.TestCase):
    """Test module path resolution."""

    def test_resolves_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            module_path = tmp / "utils.coreil.json"
            module_path.write_text("{}", encoding="utf-8")
            result = resolve_module_path("utils", tmp)
            self.assertEqual(result, module_path.resolve())

    def test_raises_on_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with self.assertRaises(ModuleNotFoundError):
                resolve_module_path("nonexistent", tmp)

    def test_dotted_path_to_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            subdir = tmp / "lib"
            subdir.mkdir()
            module_path = subdir / "helpers.coreil.json"
            module_path.write_text("{}", encoding="utf-8")
            result = resolve_module_path("lib.helpers", tmp)
            self.assertEqual(result, module_path.resolve())


class TestExtractExports(unittest.TestCase):
    """Test that extract_exports finds FuncDef nodes."""

    def test_extracts_funcdefs(self):
        doc = _make_doc([
            {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
                {"type": "Return", "value": {"type": "Binary", "op": "+",
                    "left": {"type": "Var", "name": "a"},
                    "right": {"type": "Var", "name": "b"}}},
            ]},
            {"type": "FuncDef", "name": "square", "params": ["x"], "body": [
                {"type": "Return", "value": {"type": "Binary", "op": "*",
                    "left": {"type": "Var", "name": "x"},
                    "right": {"type": "Var", "name": "x"}}},
            ]},
        ])
        exports = extract_exports(doc)
        self.assertEqual(set(exports.keys()), {"add", "square"})

    def test_ignores_non_funcdef(self):
        doc = _make_doc([
            {"type": "Let", "name": "x", "value": {"type": "Literal", "value": 42}},
            {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
                {"type": "Return", "value": {"type": "Binary", "op": "+",
                    "left": {"type": "Var", "name": "a"},
                    "right": {"type": "Var", "name": "b"}}},
            ]},
        ])
        exports = extract_exports(doc)
        self.assertEqual(set(exports.keys()), {"add"})

    def test_empty_body(self):
        doc = _make_doc([])
        exports = extract_exports(doc)
        self.assertEqual(exports, {})


class TestResolveImports(unittest.TestCase):
    """Test the import flattening logic."""

    def test_no_imports_returns_unchanged(self):
        doc = _make_doc([
            {"type": "Print", "args": [{"type": "Literal", "value": "hello"}]},
        ])
        result = resolve_imports(doc, base_dir=None)
        self.assertIs(result, doc)  # Same object, not copied

    def test_basic_import_and_call(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Write utils module
            _write_module(tmp, "utils", [
                {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "+",
                        "left": {"type": "Var", "name": "a"},
                        "right": {"type": "Var", "name": "b"}}},
                ]},
            ])

            # Main document that imports utils
            doc = _make_doc([
                {"type": "Import", "path": "utils"},
                {"type": "Let", "name": "result", "value": {
                    "type": "Call", "name": "utils.add", "args": [
                        {"type": "Literal", "value": 2},
                        {"type": "Literal", "value": 3},
                    ],
                }},
                {"type": "Print", "args": [{"type": "Var", "name": "result"}]},
            ])

            resolved = resolve_imports(doc, base_dir=tmp)

            # Import node should be removed
            import_nodes = [s for s in resolved["body"] if s.get("type") == "Import"]
            self.assertEqual(import_nodes, [])

            # Should have the inlined FuncDef with prefixed name
            func_defs = [s for s in resolved["body"] if s.get("type") == "FuncDef"]
            self.assertEqual(len(func_defs), 1)
            self.assertEqual(func_defs[0]["name"], "utils__add")

            # Call should be rewritten
            let_node = [s for s in resolved["body"] if s.get("type") == "Let"][0]
            self.assertEqual(let_node["value"]["name"], "utils__add")

    def test_import_with_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            _write_module(tmp, "math_utils", [
                {"type": "FuncDef", "name": "double", "params": ["x"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "*",
                        "left": {"type": "Var", "name": "x"},
                        "right": {"type": "Literal", "value": 2}}},
                ]},
            ])

            doc = _make_doc([
                {"type": "Import", "path": "math_utils", "alias": "mu"},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "mu.double", "args": [
                        {"type": "Literal", "value": 5},
                    ],
                }]},
            ])

            resolved = resolve_imports(doc, base_dir=tmp)

            func_defs = [s for s in resolved["body"] if s.get("type") == "FuncDef"]
            self.assertEqual(func_defs[0]["name"], "mu__double")

    def test_transitive_imports(self):
        """A imports B which imports C."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # C module: provides base_func
            _write_module(tmp, "mod_c", [
                {"type": "FuncDef", "name": "base_func", "params": [], "body": [
                    {"type": "Return", "value": {"type": "Literal", "value": 10}},
                ]},
            ])

            # B module: imports C and provides wrapper
            _write_module(tmp, "mod_b", [
                {"type": "Import", "path": "mod_c"},
                {"type": "FuncDef", "name": "wrapper", "params": [], "body": [
                    {"type": "Return", "value": {
                        "type": "Call", "name": "mod_c.base_func", "args": [],
                    }},
                ]},
            ])

            # A document: imports B
            doc = _make_doc([
                {"type": "Import", "path": "mod_b"},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "mod_b.wrapper", "args": [],
                }]},
            ])

            resolved = resolve_imports(doc, base_dir=tmp)

            # Should have both inlined funcs
            func_defs = [s for s in resolved["body"] if s.get("type") == "FuncDef"]
            func_names = {f["name"] for f in func_defs}
            self.assertIn("mod_b__wrapper", func_names)

    def test_circular_import_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # A imports B
            _write_module(tmp, "mod_a", [
                {"type": "Import", "path": "mod_b"},
                {"type": "FuncDef", "name": "func_a", "params": [], "body": [
                    {"type": "Return", "value": {"type": "Literal", "value": 1}},
                ]},
            ])

            # B imports A (circular!)
            _write_module(tmp, "mod_b", [
                {"type": "Import", "path": "mod_a"},
                {"type": "FuncDef", "name": "func_b", "params": [], "body": [
                    {"type": "Return", "value": {"type": "Literal", "value": 2}},
                ]},
            ])

            doc = _make_doc([
                {"type": "Import", "path": "mod_a"},
            ])

            with self.assertRaises(CircularImportError):
                resolve_imports(doc, base_dir=tmp)

    def test_no_base_dir_raises(self):
        doc = _make_doc([
            {"type": "Import", "path": "utils"},
        ])
        with self.assertRaises(ValueError) as cm:
            resolve_imports(doc, base_dir=None)
        self.assertIn("base_dir", str(cm.exception))


class TestInterpreterE2E(unittest.TestCase):
    """End-to-end tests: write fixture files, run interpreter, check output."""

    def test_import_and_call(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Utils module: add(a,b) and square(x)
            _write_module(tmp, "module_utils", [
                {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "+",
                        "left": {"type": "Var", "name": "a"},
                        "right": {"type": "Var", "name": "b"}}},
                ]},
                {"type": "FuncDef", "name": "square", "params": ["x"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "*",
                        "left": {"type": "Var", "name": "x"},
                        "right": {"type": "Var", "name": "x"}}},
                ]},
            ])

            # Main program
            main_doc = _make_doc([
                {"type": "Import", "path": "module_utils"},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "module_utils.add", "args": [
                        {"type": "Literal", "value": 2},
                        {"type": "Literal", "value": 3},
                    ],
                }]},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "module_utils.square", "args": [
                        {"type": "Literal", "value": 4},
                    ],
                }]},
            ])

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_coreil(main_doc, base_dir=tmp)
            self.assertEqual(rc, 0)
            self.assertEqual(buf.getvalue(), "5\n16\n")

    def test_multiple_modules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            _write_module(tmp, "greet", [
                {"type": "FuncDef", "name": "hello", "params": ["name"], "body": [
                    {"type": "Print", "args": [
                        {"type": "Literal", "value": "Hello"},
                        {"type": "Var", "name": "name"},
                    ]},
                ]},
            ])

            _write_module(tmp, "math_lib", [
                {"type": "FuncDef", "name": "triple", "params": ["x"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "*",
                        "left": {"type": "Var", "name": "x"},
                        "right": {"type": "Literal", "value": 3}}},
                ]},
            ])

            main_doc = _make_doc([
                {"type": "Import", "path": "greet"},
                {"type": "Import", "path": "math_lib"},
                {"type": "Call", "name": "greet.hello", "args": [
                    {"type": "Literal", "value": "World"},
                ]},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "math_lib.triple", "args": [
                        {"type": "Literal", "value": 7},
                    ],
                }]},
            ])

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = run_coreil(main_doc, base_dir=tmp)
            self.assertEqual(rc, 0)
            self.assertEqual(buf.getvalue(), "Hello World\n21\n")


class TestPythonParity(unittest.TestCase):
    """Verify interpreter and Python backend produce identical output."""

    def test_import_parity(self):
        from english_compiler.coreil.emit import emit_python
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Write utils module
            _write_module(tmp, "utils", [
                {"type": "FuncDef", "name": "add", "params": ["a", "b"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "+",
                        "left": {"type": "Var", "name": "a"},
                        "right": {"type": "Var", "name": "b"}}},
                ]},
                {"type": "FuncDef", "name": "square", "params": ["x"], "body": [
                    {"type": "Return", "value": {"type": "Binary", "op": "*",
                        "left": {"type": "Var", "name": "x"},
                        "right": {"type": "Var", "name": "x"}}},
                ]},
            ])

            main_doc = _make_doc([
                {"type": "Import", "path": "utils"},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "utils.add", "args": [
                        {"type": "Literal", "value": 2},
                        {"type": "Literal", "value": 3},
                    ],
                }]},
                {"type": "Print", "args": [{
                    "type": "Call", "name": "utils.square", "args": [
                        {"type": "Literal", "value": 4},
                    ],
                }]},
            ])

            # Run interpreter
            interp_buf = io.StringIO()
            with redirect_stdout(interp_buf):
                rc = run_coreil(main_doc, base_dir=tmp)
            self.assertEqual(rc, 0)
            interp_output = interp_buf.getvalue()

            # Resolve imports first (Python emitter doesn't know about modules)
            resolved = resolve_imports(main_doc, base_dir=tmp)

            # Generate and run Python code
            code, _ = emit_python(resolved)
            py_path = tmp / "test_parity.py"
            py_path.write_text(code, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(py_path)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, f"Python stderr: {result.stderr}")
            python_output = result.stdout

            # Compare
            self.assertEqual(interp_output, python_output,
                f"Parity mismatch!\nInterpreter: {interp_output!r}\nPython: {python_output!r}")


if __name__ == "__main__":
    unittest.main()
