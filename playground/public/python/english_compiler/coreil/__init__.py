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
