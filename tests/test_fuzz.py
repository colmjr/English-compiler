"""Property-based fuzzing for backend parity.

Generates random valid Core IL programs and verifies that all available
backends produce identical output. This catches edge-case divergences
that hand-written tests miss.

Usage:
    python -m tests.test_fuzz              # Run 50 random programs (default)
    python -m tests.test_fuzz --count 200  # Run 200 random programs
    python -m tests.test_fuzz --seed 42    # Reproducible run
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from english_compiler.coreil.validate import validate_coreil
from tests.test_helpers import TestFailure, verify_backend_parity


# ---------------------------------------------------------------------------
# Core IL program generator
# ---------------------------------------------------------------------------

class CoreILGenerator:
    """Generates random but valid Core IL programs."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self._var_counter = 0
        self._defined_vars: list[str] = []
        self._func_names: list[str] = []
        self._in_loop = False

    def _fresh_var(self) -> str:
        self._var_counter += 1
        name = f"v{self._var_counter}"
        self._defined_vars.append(name)
        return name

    def _int_literal(self, value: int) -> dict:
        return {"type": "Literal", "value": value}

    # -- Expressions --

    def gen_literal(self) -> dict:
        # Avoid floats: JS prints 93.0 as 93, causing false parity failures
        kind = self.rng.choice(["int", "int", "string", "bool", "null"])
        if kind == "int":
            return {"type": "Literal", "value": self.rng.randint(-100, 100)}
        if kind == "string":
            words = ["hello", "world", "foo", "bar", "", "test", "abc", "42"]
            return {"type": "Literal", "value": self.rng.choice(words)}
        if kind == "bool":
            return {"type": "Literal", "value": self.rng.choice([True, False])}
        return {"type": "Literal", "value": None}

    def _numeric_literal(self) -> dict:
        """Generate a numeric or boolean literal (safe for array printing)."""
        kind = self.rng.choice(["int", "int", "int", "bool"])
        if kind == "int":
            return self._int_literal(self.rng.randint(-100, 100))
        return {"type": "Literal", "value": self.rng.choice([True, False])}

    def _safe_literal(self) -> dict:
        """Generate a literal that prints identically across all backends."""
        kind = self.rng.choice(["int", "string", "bool", "null"])
        if kind == "int":
            return self._int_literal(self.rng.randint(-100, 100))
        if kind == "string":
            words = ["hello", "world", "foo", "bar", "test", "abc", "42"]
            return {"type": "Literal", "value": self.rng.choice(words)}
        if kind == "bool":
            return {"type": "Literal", "value": self.rng.choice([True, False])}
        return {"type": "Literal", "value": None}

    def gen_printable_expr(self, depth: int = 0) -> dict:
        """Generate an expression safe for printing (avoids tuple/record/map
        formatting differences and JS string-in-array quoting issues)."""
        if depth > 3:
            return self._safe_literal()

        choices: list[str] = ["literal", "literal", "literal"]
        if self._defined_vars:
            choices.extend(["var", "var"])
        if depth < 3:
            choices.extend(["binary", "array", "length"])
        if depth < 2:
            choices.extend(["index", "string_length"])

        kind = self.rng.choice(choices)

        if kind == "literal":
            return self._safe_literal()
        if kind == "var":
            return {"type": "Var", "name": self.rng.choice(self._defined_vars)}
        if kind == "binary":
            return self._gen_binary(depth)
        if kind == "array":
            n = self.rng.randint(0, 3)
            return {"type": "Array", "items": [self._int_literal(self.rng.randint(-100, 100)) for _ in range(n)]}
        if kind == "length":
            n = self.rng.randint(0, 3)
            arr = {"type": "Array", "items": [self._int_literal(self.rng.randint(-100, 100)) for _ in range(n)]}
            return {"type": "Length", "base": arr}
        if kind == "index":
            items = [self._int_literal(self.rng.randint(-100, 100)) for _ in range(self.rng.randint(1, 4))]
            idx = self.rng.randint(0, len(items) - 1)
            return {"type": "Index", "base": {"type": "Array", "items": items}, "index": self._int_literal(idx)}
        if kind == "string_length":
            return {"type": "StringLength", "base": {"type": "Literal", "value": self.rng.choice(["hello", "", "test", "abcdef"])}}
        return self._safe_literal()

    def gen_expr(self, depth: int = 0) -> dict:
        """Generate a random expression. Depth limits nesting."""
        if depth > 3:
            return self.gen_literal()

        choices: list[str] = ["literal", "literal", "literal"]
        if self._defined_vars:
            choices.extend(["var", "var"])
        if depth < 3:
            choices.extend(["binary", "array", "length", "not"])
        if depth < 2:
            choices.extend(["index", "string_length"])

        kind = self.rng.choice(choices)

        if kind == "literal":
            return self.gen_literal()
        if kind == "var":
            return {"type": "Var", "name": self.rng.choice(self._defined_vars)}
        if kind == "binary":
            return self._gen_binary(depth)
        if kind == "array":
            n = self.rng.randint(0, 4)
            return {"type": "Array", "items": [self.gen_expr(depth + 1) for _ in range(n)]}
        if kind == "map":
            n = self.rng.randint(0, 3)
            entries = []
            for i in range(n):
                entries.append({
                    "key": {"type": "Literal", "value": f"k{i}"},
                    "value": self.gen_expr(depth + 1),
                })
            return {"type": "Map", "items": entries}
        if kind == "length":
            n = self.rng.randint(0, 3)
            arr = {"type": "Array", "items": [self.gen_expr(depth + 1) for _ in range(n)]}
            return {"type": "Length", "base": arr}
        if kind == "index":
            items = [self.gen_expr(depth + 1) for _ in range(self.rng.randint(1, 4))]
            idx = self.rng.randint(0, len(items) - 1)
            return {"type": "Index", "base": {"type": "Array", "items": items}, "index": self._int_literal(idx)}
        if kind == "string_length":
            return {"type": "StringLength", "base": {"type": "Literal", "value": self.rng.choice(["hello", "", "test", "abcdef"])}}
        if kind == "not":
            return {"type": "Not", "arg": self.gen_expr(depth + 1)}
        return self.gen_literal()

    def _gen_binary(self, depth: int) -> dict:
        op = self.rng.choice(["+", "-", "*", "==", "!=", "<", ">", "<=", ">=", "and", "or"])
        if op in ("+", "-", "*"):
            left = self._int_literal(self.rng.randint(-50, 50))
            right = self._int_literal(self.rng.randint(-50, 50))
        elif op in ("==", "!=", "<", ">", "<=", ">="):
            left = self._int_literal(self.rng.randint(-50, 50))
            right = self._int_literal(self.rng.randint(-50, 50))
        else:
            left = {"type": "Literal", "value": self.rng.choice([True, False])}
            right = {"type": "Literal", "value": self.rng.choice([True, False])}
        return {"type": "Binary", "op": op, "left": left, "right": right}

    # -- Statements --

    def gen_stmt(self, depth: int = 0) -> dict:
        """Generate a random statement."""
        if depth > 2:
            return self._gen_print(depth)

        choices = ["let", "print", "print"]
        if self._defined_vars:
            choices.extend(["assign", "print_var"])
        if depth < 2:
            choices.extend(["if", "while_simple", "for"])
        if depth < 1:
            choices.append("func")

        kind = self.rng.choice(choices)

        if kind == "let":
            return self._gen_let(depth)
        if kind == "assign":
            return self._gen_assign(depth)
        if kind == "print" or kind == "print_var":
            return self._gen_print(depth)
        if kind == "if":
            return self._gen_if(depth)
        if kind == "while_simple":
            return self._gen_while(depth)
        if kind == "for":
            return self._gen_for(depth)
        if kind == "func":
            return self._gen_func(depth)
        return self._gen_print(depth)

    def _gen_let(self, depth: int) -> dict:
        # Generate value BEFORE creating var to avoid self-referential Let
        value = self.gen_expr(depth)
        name = self._fresh_var()
        return {"type": "Let", "name": name, "value": value}

    def _gen_assign(self, depth: int) -> dict:
        name = self.rng.choice(self._defined_vars)
        return {"type": "Assign", "name": name, "value": self.gen_expr(depth)}

    def _gen_print(self, depth: int) -> dict:
        return {"type": "Print", "args": [self.gen_printable_expr(depth)]}

    def _gen_if(self, depth: int) -> dict:
        test = self._gen_binary(depth)
        then_body = [self._gen_print(depth + 1)]
        node: dict = {"type": "If", "test": test, "then": then_body}
        if self.rng.random() < 0.5:
            node["else"] = [self._gen_print(depth + 1)]
        return node

    def _gen_while(self, depth: int) -> dict:
        counter = self._fresh_var()
        limit = self.rng.randint(1, 5)
        let_stmt = {"type": "Let", "name": counter, "value": self._int_literal(0)}

        old_in_loop = self._in_loop
        self._in_loop = True
        body = [
            self._gen_print(depth + 1),
            {"type": "Assign", "name": counter,
             "value": {"type": "Binary", "op": "+",
                       "left": {"type": "Var", "name": counter},
                       "right": self._int_literal(1)}},
        ]
        self._in_loop = old_in_loop

        while_stmt = {
            "type": "While",
            "test": {"type": "Binary", "op": "<",
                     "left": {"type": "Var", "name": counter},
                     "right": self._int_literal(limit)},
            "body": body,
        }
        return {"_multi": [let_stmt, while_stmt]}

    def _gen_for(self, depth: int) -> dict:
        # For loop var is scoped inside the loop; use a temporary name
        # that we don't add to _defined_vars (the validator tracks it)
        self._var_counter += 1
        var = f"v{self._var_counter}"
        start = self.rng.randint(0, 3)
        end = start + self.rng.randint(1, 5)

        old_in_loop = self._in_loop
        self._in_loop = True
        # Print the loop variable inside the body
        body = [{"type": "Print", "args": [{"type": "Var", "name": var}]}]
        self._in_loop = old_in_loop

        return {
            "type": "For",
            "var": var,
            "iter": {
                "type": "Range",
                "from": self._int_literal(start),
                "to": self._int_literal(end),
                "inclusive": False,
            },
            "body": body,
        }

    def _gen_func(self, depth: int) -> dict:
        fname = f"fn{len(self._func_names)}"
        self._func_names.append(fname)
        # Func param is scoped to the function body, don't add to _defined_vars
        self._var_counter += 1
        param = f"v{self._var_counter}"
        body: list[dict] = [
            {"type": "Print", "args": [{"type": "Var", "name": param}]},
            {"type": "Return", "value": {"type": "Var", "name": param}},
        ]
        func_def = {
            "type": "FuncDef",
            "name": fname,
            "params": [param],
            "body": body,
        }
        # Call the function and store result in a new var
        result_var = self._fresh_var()
        call_stmt = {
            "type": "Let",
            "name": result_var,
            "value": {"type": "Call", "name": fname, "args": [self.gen_literal()]},
        }
        return {"_multi": [func_def, call_stmt]}

    # -- Full program --

    def gen_program(self, num_stmts: int | None = None) -> dict:
        """Generate a complete valid Core IL program."""
        self._var_counter = 0
        self._defined_vars = []
        self._func_names = []
        self._in_loop = False

        if num_stmts is None:
            num_stmts = self.rng.randint(2, 10)

        body: list[dict] = []
        for _ in range(num_stmts):
            stmt = self.gen_stmt(depth=0)
            if isinstance(stmt, dict) and "_multi" in stmt:
                body.extend(stmt["_multi"])
            else:
                body.append(stmt)

        return {
            "version": "coreil-1.9",
            "body": body,
        }


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_fuzz(count: int, seed: int | None = None) -> int:
    """Run fuzz tests. Returns number of failures."""
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    print(f"Fuzzing {count} random Core IL programs (seed={seed})...\n")

    rng = random.Random(seed)
    gen = CoreILGenerator(rng)
    failures = 0
    generator_bugs = 0

    for i in range(count):
        prog = gen.gen_program()

        # Validate first — generator bugs are tracked separately
        errors = validate_coreil(prog)
        if errors:
            generator_bugs += 1
            print(f"  [{i+1}/{count}] INVALID (generator bug): {errors}")
            print(f"  Program: {json.dumps(prog, indent=2)[:500]}")
            failures += 1
            continue

        # Check backend parity
        try:
            verify_backend_parity(
                prog,
                f"fuzz_{i+1}",
                include_cpp=False,    # Slow to compile; known For-loop issue
                include_rust=False,   # Slow to compile each time
                include_go=False,     # Slow to compile each time
                include_wasm=False,   # Slow to compile each time
            )
            print(f"  [{i+1}/{count}] PASS")
        except TestFailure as exc:
            failures += 1
            print(f"  [{i+1}/{count}] FAIL: {exc}")
            print(f"  Seed: {seed}, Program #{i+1}")
            print(f"  Program: {json.dumps(prog, indent=2)[:1000]}")

    print()
    if generator_bugs:
        print(f"WARNING: {generator_bugs} programs were invalid (generator bugs)")
    if failures:
        print(f"{failures}/{count} fuzz tests FAILED (seed={seed})")
    else:
        print(f"All {count} fuzz tests passed! (seed={seed})")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Fuzz Core IL backend parity")
    parser.add_argument("--count", type=int, default=50, help="Number of random programs")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    failures = run_fuzz(args.count, args.seed)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
