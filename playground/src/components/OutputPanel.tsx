interface OutputPanelProps {
  output: string;
  error: string | null;
  isRunning: boolean;
}

export function OutputPanel({ output, error, isRunning }: OutputPanelProps) {
  return (
    <div className="output-panel">
      <div className="output-header">
        <h3>Output</h3>
        {isRunning && <span className="status loading">Running...</span>}
      </div>
      <div className={`output-content ${error ? 'error' : 'success'}`}>
        {isRunning ? (
          'Running...'
        ) : error ? (
          error
        ) : output ? (
          output
        ) : (
          <span style={{ color: 'var(--text-muted)' }}>
            Click "Run" to execute the program
          </span>
        )}
      </div>
    </div>
  );
}
