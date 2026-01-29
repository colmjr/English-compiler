import { useState, useCallback, useEffect, useRef } from 'react';

import { usePyodide } from './hooks/usePyodide';
import { useCompiler } from './hooks/useCompiler';
import { Gallery, Example } from './components/Gallery';
import { Editor } from './components/Editor';
import { EnglishEditor } from './components/EnglishEditor';
import { OutputPanel } from './components/OutputPanel';
import { PythonView } from './components/PythonView';
import { SettingsModal } from './components/SettingsModal';
import examplesData from './data/examples.json';

type Tab = 'english' | 'coreil' | 'python';

// Icon SVGs
const GearIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
);

const FolderIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
  </svg>
);

const SaveIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
    <polyline points="17 21 17 13 7 13 7 21"/>
    <polyline points="7 3 7 8 15 8"/>
  </svg>
);

function App() {
  const { status, error: pyodideError, versionInfo, runCoreIL, generatePython } = usePyodide();
  const { compile, isCompiling, hasApiKey } = useCompiler();

  const [examples] = useState<Example[]>(examplesData.examples);
  const [selectedExample, setSelectedExample] = useState<Example | null>(null);
  const [englishText, setEnglishText] = useState<string>('');
  const [coreILCode, setCoreILCode] = useState<string>('');
  const [activeTab, setActiveTab] = useState<Tab>('english');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [fileName, setFileName] = useState<string>('untitled');

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Execution state
  const [output, setOutput] = useState<string>('');
  const [execError, setExecError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // Python generation state
  const [pythonCode, setPythonCode] = useState<string>('');
  const [pythonError, setPythonError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // File operations
  const handleLoadFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      const name = file.name.replace(/\.(txt|coreil\.json|json)$/, '');
      setFileName(name);

      // Detect file type
      if (file.name.endsWith('.coreil.json') || file.name.endsWith('.json')) {
        setCoreILCode(content);
        setActiveTab('coreil');
      } else {
        setEnglishText(content);
        setActiveTab('english');
      }

      // Clear results
      setOutput('');
      setExecError(null);
      setPythonCode('');
      setPythonError(null);
      setSelectedExample(null);
    };
    reader.readAsText(file);

    // Reset input so same file can be loaded again
    e.target.value = '';
  }, []);

  const handleSaveFile = useCallback(() => {
    let content: string;
    let extension: string;
    let mimeType: string;

    if (activeTab === 'english') {
      content = englishText;
      extension = '.txt';
      mimeType = 'text/plain';
    } else if (activeTab === 'coreil') {
      content = coreILCode;
      extension = '.coreil.json';
      mimeType = 'application/json';
    } else {
      content = pythonCode;
      extension = '.py';
      mimeType = 'text/x-python';
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName + extension;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [activeTab, englishText, coreILCode, pythonCode, fileName]);

  const handleSelectExample = useCallback((example: Example) => {
    setSelectedExample(example);
    setFileName(example.id);
    // Pretty-print the JSON
    try {
      const parsed = JSON.parse(example.source);
      setCoreILCode(JSON.stringify(parsed, null, 2));
    } catch {
      setCoreILCode(example.source);
    }
    // Switch to Core IL tab when selecting an example
    setActiveTab('coreil');
    // Set expected output
    setOutput(example.expectedOutput);
    setExecError(null);
    setPythonCode('');
    setPythonError(null);
  }, []);

  const handleNewFile = useCallback(() => {
    setSelectedExample(null);
    setFileName('untitled');
    setEnglishText('');
    setCoreILCode('');
    setPythonCode('');
    setPythonError(null);
    setOutput('');
    setExecError(null);
    setActiveTab('english');
  }, []);

  const handleCompile = useCallback(async () => {
    if (!hasApiKey()) {
      setSettingsOpen(true);
      return;
    }

    const result = await compile(englishText);

    if (result.success) {
      // Pretty-print the JSON
      try {
        const parsed = JSON.parse(result.coreIL);
        setCoreILCode(JSON.stringify(parsed, null, 2));
      } catch {
        setCoreILCode(result.coreIL);
      }
      setActiveTab('coreil');
      setExecError(null);
    } else {
      setExecError(result.error);
      if (result.coreIL) {
        setCoreILCode(result.coreIL);
      }
    }
  }, [englishText, compile, hasApiKey]);

  const handleRun = useCallback(async () => {
    if (status !== 'ready') return;

    let codeToRun = coreILCode;

    // If on English tab, compile first
    if (activeTab === 'english') {
      if (!hasApiKey()) {
        setSettingsOpen(true);
        return;
      }
      const result = await compile(englishText);
      if (!result.success) {
        setExecError(result.error);
        return;
      }
      setCoreILCode(result.coreIL);
      // Use the freshly compiled code, not the stale state
      codeToRun = result.coreIL;
    }

    setIsRunning(true);
    setExecError(null);

    try {
      const result = await runCoreIL(codeToRun);
      if (result.success) {
        setOutput(result.output);
        setExecError(null);
      } else {
        setOutput(result.output);
        setExecError(result.error);
      }
    } catch (err) {
      setExecError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsRunning(false);
    }
  }, [status, activeTab, englishText, coreILCode, runCoreIL, compile, hasApiKey]);

  const handleGeneratePython = useCallback(async () => {
    if (status !== 'ready') return;

    setIsGenerating(true);
    setPythonError(null);

    try {
      const result = await generatePython(coreILCode);
      if (result.success) {
        setPythonCode(result.code);
        setPythonError(null);
      } else {
        setPythonCode('');
        setPythonError(result.error);
      }
    } catch (err) {
      setPythonError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsGenerating(false);
    }
  }, [status, coreILCode, generatePython]);

  // Auto-generate Python when switching to Python tab
  useEffect(() => {
    if (activeTab === 'python' && coreILCode && !pythonCode && !pythonError && !isGenerating && status === 'ready') {
      handleGeneratePython();
    }
  }, [activeTab, coreILCode, pythonCode, pythonError, isGenerating, status, handleGeneratePython]);

  // Clear Python when Core IL changes
  useEffect(() => {
    setPythonCode('');
    setPythonError(null);
  }, [coreILCode]);

  const getStatusText = () => {
    if (isCompiling) return 'Compiling...';
    switch (status) {
      case 'idle':
      case 'loading':
        return 'Loading Pyodide...';
      case 'ready':
        return versionInfo ? `Core IL ${versionInfo.coreil_version.replace('coreil-', 'v')}` : 'Ready';
      case 'error':
        return `Error: ${pyodideError}`;
    }
  };

  const getRunButtonText = () => {
    if (isRunning) return 'Running...';
    if (isCompiling) return 'Compiling...';
    if (activeTab === 'english') return 'Compile & Run';
    return 'Run';
  };

  return (
    <div className="app">
      {/* Loading overlay - show during idle and loading states */}
      {(status === 'idle' || status === 'loading') && (
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <div className="loading-text">Loading Python runtime...</div>
        </div>
      )}

      {/* Settings modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.json,.coreil.json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1>
            <span>English Compiler</span> Playground
          </h1>
          <span className={`status ${isCompiling ? 'loading' : status}`}>{getStatusText()}</span>
        </div>
        <div className="header-actions">
          <button
            className="icon-button"
            onClick={handleLoadFile}
            title="Open File"
          >
            <FolderIcon />
          </button>
          <button
            className="icon-button"
            onClick={handleSaveFile}
            title="Save File"
          >
            <SaveIcon />
          </button>
          <div className="header-divider" />
          {activeTab === 'english' && (
            <button
              className="secondary"
              onClick={handleCompile}
              disabled={isCompiling || !englishText.trim()}
            >
              {isCompiling ? 'Compiling...' : 'Compile'}
            </button>
          )}
          <button
            className="primary"
            onClick={handleRun}
            disabled={status !== 'ready' || isRunning || isCompiling}
          >
            {getRunButtonText()}
          </button>
          <button
            className="icon-button"
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            <GearIcon />
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="main-content">
        {/* Sidebar - Example Gallery */}
        <Gallery
          examples={examples}
          selectedId={selectedExample?.id || null}
          onSelect={handleSelectExample}
          onNew={handleNewFile}
        />

        {/* Editor area */}
        <div className="editor-area">
          {/* Tabs */}
          <div className="tabs">
            <button
              className={`tab ${activeTab === 'english' ? 'active' : ''}`}
              onClick={() => setActiveTab('english')}
            >
              English
            </button>
            <button
              className={`tab ${activeTab === 'coreil' ? 'active' : ''}`}
              onClick={() => setActiveTab('coreil')}
            >
              Core IL
            </button>
            <button
              className={`tab ${activeTab === 'python' ? 'active' : ''}`}
              onClick={() => setActiveTab('python')}
            >
              Python
            </button>
          </div>

          {/* Editor + Output */}
          <div className="editor-output-container">
            <div className="editor-panel">
              {activeTab === 'english' ? (
                <EnglishEditor
                  value={englishText}
                  onChange={setEnglishText}
                />
              ) : activeTab === 'coreil' ? (
                <Editor
                  value={coreILCode}
                  onChange={setCoreILCode}
                  language="json"
                />
              ) : (
                <PythonView
                  code={pythonCode}
                  error={pythonError}
                  isGenerating={isGenerating}
                />
              )}
            </div>
            <OutputPanel
              output={output}
              error={execError}
              isRunning={isRunning || isCompiling}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
