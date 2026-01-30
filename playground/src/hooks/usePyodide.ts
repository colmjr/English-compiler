import { useState, useEffect, useCallback, useRef } from 'react';

// Pyodide types
interface PyodideInterface {
  loadPackage: (packages: string[]) => Promise<void>;
  runPythonAsync: (code: string) => Promise<unknown>;
  FS: {
    writeFile: (path: string, data: string) => void;
    mkdir: (path: string) => void;
    readdir: (path: string) => string[];
  };
  globals: {
    get: (name: string) => unknown;
  };
}

interface LoadPyodideOptions {
  indexURL: string;
}

declare global {
  interface Window {
    loadPyodide: (options: LoadPyodideOptions) => Promise<PyodideInterface>;
  }
}

export interface RunResult {
  success: boolean;
  output: string;
  error: string | null;
}

export interface ValidateResult {
  success: boolean;
  errors: Array<{ path: string; message: string }>;
}

export interface GeneratePythonResult {
  success: boolean;
  code: string;
  error: string | null;
}

export interface VersionInfo {
  coreil_version: string;
  package_version: string;
  supported_versions: string[];
}

export type PyodideStatus = 'idle' | 'loading' | 'ready' | 'error';

export function usePyodide() {
  const [status, setStatus] = useState<PyodideStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const pyodideRef = useRef<PyodideInterface | null>(null);
  const initPromiseRef = useRef<Promise<void> | null>(null);

  // Load Pyodide and set up the Python environment
  const initialize = useCallback(async () => {
    if (pyodideRef.current) return;
    if (initPromiseRef.current) return initPromiseRef.current;

    const initPromise = (async () => {
      try {
        setStatus('loading');
        setError(null);

        // Load Pyodide from CDN
        const pyodide = await window.loadPyodide({
          indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.26.0/full/',
        });

        pyodideRef.current = pyodide;

        // Create the package directory structure
        pyodide.FS.mkdir('/home/pyodide/english_compiler');
        pyodide.FS.mkdir('/home/pyodide/english_compiler/coreil');

        // Fetch and write Python files
        const baseUrl = import.meta.env.BASE_URL || '/';
        const pythonFiles = [
          'english_compiler/__init__.py',
          'english_compiler/coreil/__init__.py',
          'english_compiler/coreil/constants.py',
          'english_compiler/coreil/versions.py',
          'english_compiler/coreil/emit_utils.py',
          'english_compiler/coreil/validate.py',
          'english_compiler/coreil/interp.py',
          'english_compiler/coreil/lower.py',
          'english_compiler/coreil/emit_base.py',
          'english_compiler/coreil/emit.py',
          'coreil_runner.py',
        ];

        for (const file of pythonFiles) {
          const response = await fetch(`${baseUrl}python/${file}`);
          if (!response.ok) {
            throw new Error(`Failed to fetch ${file}: ${response.status}`);
          }
          const content = await response.text();
          const destPath = `/home/pyodide/${file}`;
          pyodide.FS.writeFile(destPath, content);
        }

        // Add to Python path and import the runner
        await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, '/home/pyodide')
import coreil_runner
`);

        // Get version info
        const versionJson = await pyodide.runPythonAsync('coreil_runner.get_version()') as string;
        setVersionInfo(JSON.parse(versionJson));

        setStatus('ready');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setError(message);
        setStatus('error');
        throw err;
      }
    })();

    initPromiseRef.current = initPromise;
    return initPromise;
  }, []);

  // Initialize on mount
  useEffect(() => {
    // Load Pyodide script
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/pyodide/v0.26.0/full/pyodide.js';
    script.async = true;
    script.onload = () => {
      initialize();
    };
    script.onerror = () => {
      setError('Failed to load Pyodide script');
      setStatus('error');
    };
    document.head.appendChild(script);

    return () => {
      // Cleanup script on unmount
      document.head.removeChild(script);
    };
  }, [initialize]);

  // Helper to encode string as base64
  const toBase64 = (str: string): string => {
    const encoder = new TextEncoder();
    const bytes = encoder.encode(str);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  // Run Core IL program
  const runCoreIL = useCallback(async (jsonStr: string): Promise<RunResult> => {
    if (!pyodideRef.current) {
      return { success: false, output: '', error: 'Pyodide not initialized' };
    }

    try {
      const b64 = toBase64(jsonStr);
      const resultJson = await pyodideRef.current.runPythonAsync(
        `coreil_runner.run_b64("${b64}")`
      ) as string;
      return JSON.parse(resultJson);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, output: '', error: message };
    }
  }, []);

  // Validate Core IL program
  const validateCoreIL = useCallback(async (jsonStr: string): Promise<ValidateResult> => {
    if (!pyodideRef.current) {
      return { success: false, errors: [{ path: '$', message: 'Pyodide not initialized' }] };
    }

    try {
      const b64 = toBase64(jsonStr);
      const resultJson = await pyodideRef.current.runPythonAsync(
        `coreil_runner.validate_b64("${b64}")`
      ) as string;
      return JSON.parse(resultJson);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, errors: [{ path: '$', message }] };
    }
  }, []);

  // Generate Python code
  const generatePython = useCallback(async (jsonStr: string): Promise<GeneratePythonResult> => {
    if (!pyodideRef.current) {
      return { success: false, code: '', error: 'Pyodide not initialized' };
    }

    try {
      const b64 = toBase64(jsonStr);
      const resultJson = await pyodideRef.current.runPythonAsync(
        `coreil_runner.generate_python_b64("${b64}")`
      ) as string;
      return JSON.parse(resultJson);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      return { success: false, code: '', error: message };
    }
  }, []);

  return {
    status,
    error,
    versionInfo,
    runCoreIL,
    validateCoreIL,
    generatePython,
  };
}
