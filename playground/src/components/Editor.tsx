import MonacoEditor from '@monaco-editor/react';

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  language?: string;
  readOnly?: boolean;
}

export function Editor({ value, onChange, language = 'json', readOnly = false }: EditorProps) {
  return (
    <div className="monaco-container">
      <MonacoEditor
        height="100%"
        language={language}
        value={value}
        onChange={(val) => onChange(val || '')}
        theme="vs-dark"
        loading={<div className="editor-loading">Loading editor...</div>}
        options={{
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          readOnly,
          renderLineHighlight: 'line',
          padding: { top: 12, bottom: 12 },
        }}
      />
    </div>
  );
}
