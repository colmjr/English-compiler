import MonacoEditor from '@monaco-editor/react';

interface EnglishEditorProps {
  value: string;
  onChange: (value: string) => void;
}

const PLACEHOLDER_TEXT = `# Write your program in plain English

# Examples:
Print "Hello, World!"

Calculate the sum of numbers from 1 to 100 and print it

Sort the array [5, 2, 8, 1, 9] using bubble sort and print the result

# Tips:
# - Be specific about what you want to print
# - Describe algorithms step by step
# - Click "Compile" to generate Core IL, then "Run" to execute
`;

export function EnglishEditor({ value, onChange }: EnglishEditorProps) {
  const isEmpty = !value || value.trim() === '';

  return (
    <div className="monaco-container" style={{ position: 'relative' }}>
      {isEmpty && (
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: 66,
            right: 16,
            color: 'var(--text-muted)',
            pointerEvents: 'none',
            zIndex: 1,
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace',
            fontSize: 14,
            lineHeight: '24px',
            opacity: 0.6,
          }}
        >
          {PLACEHOLDER_TEXT}
        </div>
      )}
      <MonacoEditor
        height="100%"
        language="plaintext"
        value={value}
        onChange={(val) => onChange(val || '')}
        theme="vs-dark"
        loading={<div className="editor-loading">Loading editor...</div>}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          renderLineHighlight: 'line',
          padding: { top: 16, bottom: 16 },
          lineHeight: 24,
        }}
      />
    </div>
  );
}
