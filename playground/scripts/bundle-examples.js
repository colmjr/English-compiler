#!/usr/bin/env node
/**
 * Bundle examples for the playground.
 *
 * This script reads all .coreil.json files from the examples directory,
 * runs each through the Python interpreter to capture expected output,
 * and generates a JSON file with metadata for the gallery.
 */

import { execFileSync } from "child_process";
import {
  readFileSync,
  writeFileSync,
  readdirSync,
  mkdirSync,
  existsSync,
} from "fs";
import { join, dirname, basename } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PLAYGROUND_DIR = dirname(__dirname);
const PROJECT_ROOT = dirname(PLAYGROUND_DIR);
const EXAMPLES_DIR = join(PROJECT_ROOT, "examples");
const OUTPUT_FILE = join(PLAYGROUND_DIR, "src", "data", "examples.json");
const PYTHON_CANDIDATES = [process.env.PYTHON, "python3", "python"].filter(
  Boolean,
);

// Example categories for organization
const CATEGORIES = {
  Basics: ["hello", "if", "for_sum", "foreach_print"],
  Arrays: [
    "array_index",
    "array_setindex",
    "array_length",
    "array_negative_index",
    "slice_test",
  ],
  Functions: ["fn_add"],
  "Data Structures": [
    "map_demo",
    "record_demo",
    "queue_demo",
    "heap_demo",
    "heap_kth_smallest",
  ],
  Algorithms: ["bubble_sort"],
  Math: ["math", "math_basic", "math_comprehensive"],
  Strings: ["string_ops"],
  "JSON & Regex": ["json_basic", "regex_basic"],
};

// Examples to skip (non-portable or problematic)
const SKIP_EXAMPLES = ["external_call_demo"];

function getCategory(name) {
  for (const [category, examples] of Object.entries(CATEGORIES)) {
    if (examples.includes(name)) {
      return category;
    }
  }
  return "Other";
}

function getDisplayName(filename) {
  // Convert filename to display name
  // e.g., "hello" -> "Hello World", "for_sum" -> "For Loop Sum"
  const nameMap = {
    hello: "Hello World",
    if: "If Statement",
    for_sum: "For Loop Sum",
    foreach_print: "ForEach Print",
    array_index: "Array Indexing",
    array_setindex: "Array Set Index",
    array_length: "Array Length",
    array_negative_index: "Negative Indexing",
    slice_test: "Array Slicing",
    fn_add: "Function Add",
    map_demo: "Map/Dictionary",
    record_demo: "Records",
    queue_demo: "Deque (Queue)",
    heap_demo: "Heap (Priority Queue)",
    heap_kth_smallest: "Heap: Kth Smallest",
    bubble_sort: "Bubble Sort",
    math: "Math Operations",
    math_basic: "Basic Math",
    math_comprehensive: "Comprehensive Math",
    string_ops: "String Operations",
    json_basic: "JSON Parse/Stringify",
    regex_basic: "Regex Operations",
  };

  if (nameMap[filename]) {
    return nameMap[filename];
  }

  // Default: convert snake_case to Title Case
  return filename
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function runPython(code) {
  let lastError = null;

  for (const pythonCmd of PYTHON_CANDIDATES) {
    try {
      return execFileSync(pythonCmd, ["-c", code], {
        encoding: "utf-8",
        timeout: 10000,
      });
    } catch (error) {
      if (error?.code === "ENOENT") {
        lastError = error;
        continue;
      }
      throw error;
    }
  }

  throw (
    lastError ||
    new Error(
      "No Python interpreter found. Set PYTHON, or install python3/python.",
    )
  );
}

function runExample(coreilPath) {
  try {
    // Use the Python interpreter to run the example
    const result = runPython(`
import json
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(PROJECT_ROOT)})
from english_compiler.coreil import run_coreil

with open(${JSON.stringify(coreilPath)}) as f:
    doc = json.load(f)

old_stdout = sys.stdout
sys.stdout = captured = StringIO()
errors = []
def error_callback(msg):
    errors.append(msg)

exit_code = run_coreil(
    doc,
    error_callback=error_callback,
    base_dir=Path(${JSON.stringify(EXAMPLES_DIR)}),
)
output = captured.getvalue()
sys.stdout = old_stdout

result = {
    'success': exit_code == 0 and len(errors) == 0,
    'output': output,
    'error': '\\n'.join(errors) if errors else None
}
print(json.dumps(result))
`);
    return JSON.parse(result.trim());
  } catch (error) {
    return {
      success: false,
      output: "",
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

function main() {
  console.log("Bundling examples for playground...\n");

  // Ensure output directory exists
  const outputDir = dirname(OUTPUT_FILE);
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
  }

  // Find all .coreil.json files
  const files = readdirSync(EXAMPLES_DIR)
    .filter((f) => f.endsWith(".coreil.json"))
    .filter((f) => !SKIP_EXAMPLES.includes(basename(f, ".coreil.json")));

  console.log(`Found ${files.length} example files\n`);

  const examples = [];

  for (const file of files) {
    const name = basename(file, ".coreil.json");
    const filePath = join(EXAMPLES_DIR, file);

    console.log(`Processing: ${name}`);

    // Read the Core IL source
    const source = readFileSync(filePath, "utf-8");
    let doc;
    try {
      doc = JSON.parse(source);
    } catch (e) {
      console.log(`  ERROR: Invalid JSON - ${e.message}`);
      continue;
    }

    // Run to get expected output
    const result = runExample(filePath);

    if (result.success) {
      console.log(
        `  OK: "${result.output.trim().substring(0, 50)}${result.output.length > 50 ? "..." : ""}"`,
      );
    } else {
      console.log(`  SKIP: ${result.error || "Unknown error"}`);
      continue;
    }

    examples.push({
      id: name,
      name: getDisplayName(name),
      category: getCategory(name),
      source: source,
      expectedOutput: result.output,
      version: doc.version || "coreil-1.0",
    });
  }

  // Sort examples by category and name
  examples.sort((a, b) => {
    if (a.category !== b.category) {
      // Custom category order
      const categoryOrder = [
        "Basics",
        "Arrays",
        "Functions",
        "Data Structures",
        "Algorithms",
        "Math",
        "Strings",
        "JSON & Regex",
        "Other",
      ];
      return (
        categoryOrder.indexOf(a.category) - categoryOrder.indexOf(b.category)
      );
    }
    return a.name.localeCompare(b.name);
  });

  // Write output
  const output = {
    generatedAt: new Date().toISOString(),
    count: examples.length,
    examples: examples,
  };

  writeFileSync(OUTPUT_FILE, JSON.stringify(output, null, 2));

  console.log(`\nGenerated ${OUTPUT_FILE}`);
  console.log(`Total: ${examples.length} examples bundled`);

  // Print summary by category
  const byCategory = {};
  for (const ex of examples) {
    byCategory[ex.category] = (byCategory[ex.category] || 0) + 1;
  }
  console.log("\nBy category:");
  for (const [cat, count] of Object.entries(byCategory)) {
    console.log(`  ${cat}: ${count}`);
  }
}

main();
