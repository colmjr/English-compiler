"""Tests for WASM host readASString function.

Tests the JavaScript readASString function used in wasm_build.py:run_wasm()
for decoding AssemblyScript strings from WASM linear memory.

Requires Node.js; skips gracefully if unavailable.

Run with: python -m tests.test_wasm_host_print
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


_NODE_AVAILABLE = shutil.which("node") is not None


# The readASString function extracted from wasm_build.py, plus a test harness
# that builds synthetic ArrayBuffers mimicking AS string memory layout.
_TEST_SCRIPT = r"""
// readASString: decode an AssemblyScript string from a memory buffer.
// Layout: [4-byte byte-length at ptr-4][UTF-16LE data at ptr]
function readASString(buffer, ptr) {
    if (ptr === 0) return "";
    const bytes = new Uint8Array(buffer);
    const byteLength = (
        bytes[ptr - 4] |
        (bytes[ptr - 3] << 8) |
        (bytes[ptr - 2] << 16) |
        (bytes[ptr - 1] << 24)
    ) >>> 0;
    if (byteLength === 0) return "";
    const u16 = new Uint16Array(buffer, ptr, byteLength >> 1);
    return String.fromCharCode(...u16);
}

// Helper: build a buffer with an AS-format string at a given offset.
// Returns { buffer, ptr } where ptr points to the string data (after the length prefix).
function makeASString(str) {
    const headerSize = 4; // 4-byte length prefix
    const dataBytes = str.length * 2; // UTF-16LE: 2 bytes per char
    const totalSize = headerSize + dataBytes;
    // Ensure 8-byte alignment for ptr so Uint16Array works
    const offset = 8; // start after some padding
    const buf = new ArrayBuffer(offset + totalSize);
    const view = new DataView(buf);
    // Write byte-length (little-endian) at ptr - 4
    const ptr = offset + headerSize;
    view.setUint32(ptr - 4, dataBytes, true); // true = little-endian
    // Write UTF-16LE data
    for (let i = 0; i < str.length; i++) {
        view.setUint16(ptr + i * 2, str.charCodeAt(i), true);
    }
    return { buffer: buf, ptr: ptr };
}

let passed = 0;
let failed = 0;

function assert(condition, name) {
    if (condition) {
        console.log("  " + name + ": PASS");
        passed++;
    } else {
        console.log("  " + name + ": FAIL");
        failed++;
    }
}

// Test 1: null pointer returns empty string
{
    const buf = new ArrayBuffer(64);
    const result = readASString(buf, 0);
    assert(result === "", "null_pointer");
}

// Test 2: ASCII string "hello"
{
    const { buffer, ptr } = makeASString("hello");
    const result = readASString(buffer, ptr);
    assert(result === "hello", "ascii_string (got: " + JSON.stringify(result) + ")");
}

// Test 3: Unicode string with accented characters
{
    const { buffer, ptr } = makeASString("caf\u00e9");
    const result = readASString(buffer, ptr);
    assert(result === "caf\u00e9", "unicode_string (got: " + JSON.stringify(result) + ")");
}

console.log();
console.log(passed + "/" + (passed + failed) + " passed");
process.exit(failed > 0 ? 1 : 0);
"""


def test_wasm_host_print() -> None:
    """Run the Node.js test script that validates readASString."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(_TEST_SCRIPT)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["node", tmp_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(result.stdout, end="")
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, end="")
            raise AssertionError("Node.js readASString tests failed")
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main() -> int:
    if not _NODE_AVAILABLE:
        print("Node.js not available - skipping WASM host print tests")
        return 0

    print("Running WASM host print tests...\n")

    try:
        test_wasm_host_print()
    except AssertionError as e:
        print(f"\nFAILED: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: {e}")
        return 1

    print("All WASM host print tests passed! \u2713")
    return 0


if __name__ == "__main__":
    sys.exit(main())
