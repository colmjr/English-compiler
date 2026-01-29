#!/bin/bash
# Copy Python modules from english_compiler/coreil to playground/public/python
# This script creates a browser-compatible Python package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYGROUND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$PLAYGROUND_DIR")"
COREIL_SRC="$PROJECT_ROOT/english_compiler/coreil"
PYTHON_DEST="$PLAYGROUND_DIR/public/python/english_compiler/coreil"

echo "Copying Python modules for Pyodide..."

# Create destination directory structure
mkdir -p "$PYTHON_DEST"

# Create __init__.py files for package structure
mkdir -p "$PLAYGROUND_DIR/public/python/english_compiler"
echo '"""English Compiler package (browser-compatible subset)."""' > "$PLAYGROUND_DIR/public/python/english_compiler/__init__.py"

cat > "$PYTHON_DEST/__init__.py" << 'EOF'
"""Core IL package for browser environment.

This is a browser-compatible subset of the english_compiler.coreil package,
designed to run in Pyodide.
"""

from .versions import COREIL_VERSION, SUPPORTED_VERSIONS, PACKAGE_VERSION
from .validate import validate_coreil
from .interp import run_coreil
from .emit import emit_python

__all__ = [
    'COREIL_VERSION',
    'SUPPORTED_VERSIONS',
    'PACKAGE_VERSION',
    'validate_coreil',
    'run_coreil',
    'emit_python',
]
EOF

# Copy required modules
cp "$COREIL_SRC/constants.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/versions.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/emit_utils.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/validate.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/interp.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/lower.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/emit_base.py" "$PYTHON_DEST/"
cp "$COREIL_SRC/emit.py" "$PYTHON_DEST/"

echo "Python modules copied successfully to $PYTHON_DEST"
