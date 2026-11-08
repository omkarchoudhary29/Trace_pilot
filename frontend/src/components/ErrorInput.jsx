import React from 'react';

export default function ErrorInput({
  errorText,
  setErrorText,
  language,
  setLanguage,
  isStreaming,
  setIsStreaming,
  isStructured,
  setIsStructured,
  examples,
  onAnalyze,
  onClear,
  isLoading,
}) {
  const handleSelectExample = (ex) => {
    setErrorText(ex.error_text);
    if (ex.programming_language) {
      setLanguage(ex.programming_language.toLowerCase());
    }
  };

  return (
    <div className="card" style={{ marginBottom: '1.5rem' }}>
      <div className="card-header" style={{ alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
            Error & Traceback Submission
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Paste a stack trace, runtime exception, database log, or HTTP error. Credentials and API keys are automatically redacted.
          </p>
        </div>

        {/* Preset Selector */}
        {examples && examples.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.35rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 500 }}>Load Benchmark Presets:</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', justifyContent: 'flex-end' }}>
              {examples.slice(0, 5).map((ex) => (
                <button
                  key={ex.id}
                  type="button"
                  onClick={() => handleSelectExample(ex)}
                  className="btn btn-preset"
                  title={ex.description}
                  disabled={isLoading}
                >
                  {ex.title}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Textarea */}
      <div style={{ position: 'relative', marginBottom: '1rem' }}>
        <textarea
          value={errorText}
          onChange={(e) => setErrorText(e.target.value)}
          placeholder="Paste error traceback, console exception, or application log here...
Example:
Traceback (most recent call last):
  File 'calculator.py', line 18, in calculate_total
    return subtotal + tax_rate
TypeError: unsupported operand type(s) for +: 'int' and 'str'"
          rows={9}
          disabled={isLoading}
          style={{
            width: '100%',
            background: '#060a12',
            border: '1px solid var(--border-color)',
            borderRadius: 6,
            padding: '1rem',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.875rem',
            lineHeight: 1.6,
            resize: 'vertical',
            outline: 'none',
            transition: 'border-color 0.2s ease',
          }}
          onFocus={(e) => (e.target.style.borderColor = 'var(--border-focus)')}
          onBlur={(e) => (e.target.style.borderColor = 'var(--border-color)')}
        />
        <div style={{ position: 'absolute', bottom: '1rem', right: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {errorText.length} / 10000 chars
        </div>
      </div>

      {/* Action and Configuration Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
          {/* Language selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label htmlFor="lang-select" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
              Language:
            </label>
            <select
              id="lang-select"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={isLoading}
              style={{
                background: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 4,
                padding: '0.35rem 0.65rem',
                fontSize: '0.8rem',
                outline: 'none',
              }}
            >
              <option value="auto">Auto-Detect</option>
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="sql">SQL / Database</option>
              <option value="http">HTTP / API</option>
              <option value="log">Log Trace</option>
            </select>
          </div>

          {/* Streaming Toggle */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isStreaming}
              onChange={(e) => setIsStreaming(e.target.checked)}
              disabled={isLoading}
              style={{ accentColor: 'var(--accent-cyan)' }}
            />
            <span>Real-Time Streaming (SSE)</span>
          </label>

          {/* Structured Output Toggle */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isStructured}
              onChange={(e) => setIsStructured(e.target.checked)}
              disabled={isLoading}
              style={{ accentColor: 'var(--accent-cyan)' }}
            />
            <span>Structured Pydantic Engine</span>
          </label>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={onClear}
            disabled={isLoading || (!errorText && !isLoading)}
            className="btn btn-secondary"
          >
            Clear
          </button>
          <button
            type="button"
            onClick={onAnalyze}
            disabled={isLoading || !errorText.trim()}
            className="btn btn-primary"
            style={{ minWidth: 140 }}
          >
            {isLoading ? (
              <>
                <span style={{ display: 'inline-block', width: 14, height: 14, border: '2px solid rgba(0,0,0,0.2)', borderTopColor: '#000', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>Analyze Error</span>
              </>
            )}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

