# English Compiler Playground

A browser-based playground for writing English pseudocode and compiling it to executable code. Uses Pyodide (Python in WebAssembly) to run the interpreter entirely client-side.

## Features

- **Write English pseudocode** and compile to Core IL using Claude or GPT-4
- **Run Core IL programs** directly in your browser
- **Gallery of 22+ examples** organized by category
- **Monaco editor** with syntax highlighting
- **View generated Python code** for any Core IL program
- **No backend server** - API calls go directly to Anthropic/OpenAI

## Getting Started

1. Click the gear icon to open Settings
2. Choose your LLM provider (Anthropic or OpenAI)
3. Enter your API key
4. Write English in the English tab
5. Click "Compile & Run"

## Development

### Prerequisites

- Node.js 18+
- Python 3.10+ (for bundling examples)

### Setup

```bash
# Install dependencies
npm install

# Copy Python modules
npm run copy-python

# Bundle examples
npm run bundle-examples
```

### Development Server

```bash
npm run dev
```

Opens at http://localhost:5173/english-compiler/

### Production Build

```bash
npm run build
npm run preview  # Test production build locally
```

## Architecture

```
playground/
├── src/
│   ├── components/       # React components
│   │   ├── Gallery.tsx   # Example selector sidebar
│   │   ├── Editor.tsx    # Monaco editor wrapper
│   │   ├── OutputPanel.tsx
│   │   └── PythonView.tsx
│   ├── hooks/
│   │   └── usePyodide.ts # Pyodide loading and execution
│   ├── data/
│   │   └── examples.json # Generated example data
│   └── App.tsx           # Main application
├── public/
│   └── python/           # Python modules for Pyodide
│       ├── coreil_runner.py
│       └── english_compiler/coreil/
├── scripts/
│   ├── bundle-examples.js
│   └── copy-python.sh
└── dist/                 # Production build output
```

## Deployment

The playground is automatically deployed to GitHub Pages when changes are pushed to:
- `playground/**`
- `examples/**`
- `english_compiler/coreil/**`

Live URL: https://colmjr.github.io/english-compiler/

## Technology Stack

- **Vite** - Build tool
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Monaco Editor** - Code editing
- **Pyodide** - Python in WebAssembly
- **Allotment** - Resizable split panes
