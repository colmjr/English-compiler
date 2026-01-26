"""English Compiler - Translate English pseudocode to executable code.

The English Compiler translates English pseudocode into executable code
through a deterministic intermediate representation (Core IL).

Example usage:
    # Compile a file
    python -m english_compiler compile examples/hello.txt

    # Run Core IL directly
    python -m english_compiler run examples/hello.coreil.json

For programmatic use:
    from english_compiler.coreil import validate_coreil, interp

    # Load and validate Core IL
    with open("program.coreil.json") as f:
        program = json.load(f)
    validate_coreil(program)

    # Execute
    interp(program)
"""

from english_compiler.coreil.versions import PACKAGE_VERSION

__version__ = PACKAGE_VERSION
__all__ = ["__version__"]
