import React, { useEffect, useState } from 'react';
import Navbar from './components/Navbar';
import ErrorInput from './components/ErrorInput';
import DebugReport from './components/DebugReport';
import EvaluationView from './components/EvaluationView';
import { fetchExamples, fetchHealth, submitDebugRequest, streamDebugRequest } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('debugger');
  const [health, setHealth] = useState(null);
  const [examples, setExamples] = useState([]);

  // Input states
  const [errorText, setErrorText] = useState('');
  const [language, setLanguage] = useState('auto');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isStructured, setIsStructured] = useState(true);

  // Execution states
  const [isLoading, setIsLoading] = useState(false);
  const [streamProgress, setStreamProgress] = useState('');
  const [report, setReport] = useState(null);
  const [rawText, setRawText] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => console.warn('Health check unavailable:', err.message));

    fetchExamples()
      .then(setExamples)
      .catch((err) => console.warn('Could not load preset benchmark examples:', err.message));
  }, []);

  const handleClear = () => {
    setErrorText('');
    setReport(null);
    setRawText(null);
    setMetrics(null);
    setStreamProgress('');
    setErrorMessage(null);
  };

  const handleAnalyze = async () => {
    if (!errorText.trim()) return;

    setIsLoading(true);
    setErrorMessage(null);
    setReport(null);
    setRawText(null);
    setMetrics(null);
    setStreamProgress('');

    if (isStreaming) {
      // Streaming execution path via SSE
      await streamDebugRequest({
        errorText,
        language,
        structured: isStructured,
        onChunk: (delta) => {
          setStreamProgress((prev) => prev + delta);
        },
        onCompleted: (data) => {
          setIsLoading(false);
          setRawText(data.raw_text);
          setReport(data.report);
          setMetrics(data.metrics);
        },
        onError: (err) => {
          setIsLoading(false);
          setErrorMessage(err.message || 'Stream processing failed.');
        },
      });
    } else {
      // Synchronous execution path
      try {
        const result = await submitDebugRequest({
          errorText,
          language,
          structured: isStructured,
        });

        setIsLoading(false);
        setReport(result.report);
        setRawText(result.raw_text);
        setMetrics(result.metrics);
      } catch (err) {
        setIsLoading(false);
        setErrorMessage(err.message || 'An unexpected failure occurred during analysis.');
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} health={health} />

      <main className="container" style={{ flex: 1, paddingBottom: '3rem' }}>
        {activeTab === 'debugger' ? (
          <div>
            {/* Error Banner */}
            {errorMessage && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 8,
                padding: '1rem 1.25rem',
                marginBottom: '1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#f87171',
                fontSize: '0.875rem',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <span style={{ fontSize: '1.25rem' }}>⚠️</span>
                  <span>{errorMessage}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorMessage(null)}
                  style={{ background: 'transparent', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: '1.1rem' }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* Error Input Panel */}
            <ErrorInput
              errorText={errorText}
              setErrorText={setErrorText}
              language={language}
              setLanguage={setLanguage}
              isStreaming={isStreaming}
              setIsStreaming={setIsStreaming}
              isStructured={isStructured}
              setIsStructured={setIsStructured}
              examples={examples}
              onAnalyze={handleAnalyze}
              onClear={handleClear}
              isLoading={isLoading}
            />

            {/* Streaming in-progress preview */}
            {isLoading && isStreaming && streamProgress && (
              <div className="card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--accent-indigo)' }}>
                <div className="card-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: 'var(--accent-indigo)', animation: 'pulse 1.2s infinite' }} />
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--accent-indigo)' }}>
                      Receiving Real-Time Response Stream...
                    </h3>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Pydantic schema validation runs upon stream completion
                  </span>
                </div>
                <div className="code-block">
                  <pre>{streamProgress}</pre>
                </div>
              </div>
            )}

            {/* Structured Report Display */}
            {(report || rawText) && (
              <DebugReport report={report} rawText={rawText} metrics={metrics} />
            )}
          </div>
        ) : (
          <EvaluationView />
        )}
      </main>

      <footer style={{
        borderTop: '1px solid var(--border-color)',
        padding: '1.5rem',
        textAlign: 'center',
        fontSize: '0.8rem',
        color: 'var(--text-muted)',
      }}>
        TracePilot Portfolio Application • Multi-Model Failover Architecture (`gemini-3.5-flash-lite` → `gemini-3.5-flash`) • Zero Code Execution
      </footer>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.9); }
        }
      `}</style>
    </div>
  );
}

