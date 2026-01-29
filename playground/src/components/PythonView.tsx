import MonacoEditor from '@monaco-editor/react';

interface PythonViewProps {
  code: string;
  error: string | null;
  isGenerating: boolean;
}

export function PythonView({ code, error, isGenerating }: PythonViewProps) {
  if (isGenerating) {
    return (
      <div className="python-view" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="status loading">Generating Python...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="python-view" style={{ padding: 16 }}>
        <div className="output-content error">{error}</div>
      </div>
    );
  }

  if (!code) {
    return (
      <div className="python-view" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
        Generated Python code will appear here
      </div>
    );
  }

  return (
    <div className="python-view">
      <MonacoEditor
        height="100%"
        language="python"
        value={code}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          wordWrap: 'on',
          readOnly: true,
          renderLineHighlight: 'none',
          padding: { top: 12, bottom: 12 },
        }}
      />
    </div>
  );
}
