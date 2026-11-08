import React, { useState } from 'react';

export default function DebugReport({ report, rawText, metrics }) {
  const [copied, setCopied] = useState(false);

  // If unstructured string report
  if (!report) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Unstructured Debugging Analysis</h2>
        </div>
        <div className="code-block" style={{ color: 'var(--text-primary)' }}>
          <pre>{rawText || 'No report content available.'}</pre>
        </div>
      </div>
    );
  }

  const {
    error_information: errInfo = {},
    error_summary: summary = {},
    evidence = {},
    root_cause_analysis: rootCause = {},
    debugging_steps: steps = [],
    suggested_fix: fix = {},
    verification = {},
    confidence_and_review: confidence = {},
  } = report;

  const handleCopyCode = () => {
    if (fix.code_example) {
      navigator.clipboard.writeText(fix.code_example);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const severityBadgeClass = `badge badge-${(errInfo.severity || 'medium').toLowerCase()}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* 1. Error Overview Card */}
      <div className="card" style={{ borderLeft: '4px solid var(--accent-cyan)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span className={severityBadgeClass}>
              {errInfo.severity || 'Medium'} Severity
            </span>
            <span className="badge badge-info">
              {errInfo.category || 'Runtime'}
            </span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Language: <strong style={{ color: 'var(--text-secondary)' }}>{errInfo.programming_language || 'Unknown'}</strong>
            </span>
          </div>

          {(errInfo.filename || errInfo.line_number) && (
            <div style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', background: 'rgba(56, 189, 248, 0.08)', padding: '0.2rem 0.5rem', borderRadius: 4 }}>
              📍 {errInfo.filename || 'unknown'}{errInfo.line_number ? `:${errInfo.line_number}` : ''}
              {errInfo.function_name ? ` in ${errInfo.function_name}()` : ''}
            </div>
          )}
        </div>

        <h1 style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
          {errInfo.error_type || 'Software Error'}
        </h1>
        <p style={{ fontSize: '0.95rem', fontFamily: 'var(--font-mono)', color: '#f87171' }}>
          {errInfo.error_message || 'No detailed error message provided.'}
        </p>
      </div>

      {/* 2. Summary Card */}
      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Summary
        </h3>
        <p style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.5rem', lineHeight: 1.6 }}>
          {summary.short_description || summary.plain_language_explanation}
        </p>
        {summary.failed_operation && (
          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            <strong>Failed Operation:</strong> {summary.failed_operation}
          </div>
        )}
      </div>

      {/* 3. Evidence & Grounding Card */}
      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Evidence from Original Trace
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          {/* Observed Facts */}
          <div style={{ background: '#0a0f1d', padding: '0.875rem', borderRadius: 6, border: '1px solid var(--border-color)' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-emerald)', marginBottom: '0.5rem' }}>
              ✓ Observed Facts (Directly in Trace)
            </h4>
            <ul style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', paddingLeft: '1.25rem', lineHeight: 1.6 }}>
              {evidence.observed_facts && evidence.observed_facts.length > 0 ? (
                evidence.observed_facts.map((fact, i) => <li key={i}>{fact}</li>)
              ) : (
                <li>No direct trace facts isolated.</li>
              )}
            </ul>
          </div>

          {/* Inferred Conclusions */}
          <div style={{ background: '#0a0f1d', padding: '0.875rem', borderRadius: 6, border: '1px solid var(--border-color)' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-amber)', marginBottom: '0.5rem' }}>
              💡 Inferred Context (Deductions)
            </h4>
            <ul style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', paddingLeft: '1.25rem', lineHeight: 1.6 }}>
              {evidence.inferred_information && evidence.inferred_information.length > 0 ? (
                evidence.inferred_information.map((inf, i) => <li key={i}>{inf}</li>)
              ) : (
                <li>No secondary inferences derived.</li>
              )}
            </ul>
          </div>
        </div>
      </div>

      {/* 4. Root Cause Analysis Card */}
      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Root Cause Analysis
        </h3>
        {rootCause.primary_hypothesis && (
          <div style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)', padding: '1rem', borderRadius: 6, marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>PRIMARY HYPOTHESIS</span>
              <span className="badge badge-info">{rootCause.primary_hypothesis.confidence || 'High'} Confidence</span>
            </div>
            <p style={{ fontSize: '0.95rem', color: 'var(--text-primary)', fontWeight: 500 }}>
              {rootCause.primary_hypothesis.hypothesis}
            </p>
          </div>
        )}

        {rootCause.alternative_hypotheses && rootCause.alternative_hypotheses.length > 0 && (
          <div>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>Alternative Hypotheses:</h4>
            <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: '1.25rem', lineHeight: 1.5 }}>
              {rootCause.alternative_hypotheses.map((alt, i) => (
                <li key={i}>{alt.hypothesis} ({alt.confidence} confidence)</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 5. Recommended Debugging Steps Card */}
      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Actionable Debugging Steps
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {steps.map((step) => (
            <div key={step.step_number} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{
                background: 'var(--bg-card)',
                color: 'var(--accent-cyan)',
                border: '1px solid var(--border-color)',
                width: 26,
                height: 26,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.8rem',
                fontWeight: 700,
                flexShrink: 0,
              }}>
                {step.step_number}
              </div>
              <div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {step.action}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <strong>Why:</strong> {step.why_recommended}
                  {step.expected_outcome && <> • <strong>Expected:</strong> {step.expected_outcome}</>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 6. Suggested Fix Card */}
      {fix.explanation && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Suggested Fix
            </h3>
            {fix.code_example && (
              <button
                type="button"
                onClick={handleCopyCode}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem' }}
              >
                {copied ? '✓ Copied' : 'Copy Code'}
              </button>
            )}
          </div>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
            {fix.explanation}
          </p>
          {fix.code_example && (
            <div className="code-block" style={{ marginBottom: '0.75rem' }}>
              <pre>{fix.code_example}</pre>
            </div>
          )}
          {fix.where_to_apply && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <strong>Where to apply:</strong> {fix.where_to_apply}
            </div>
          )}
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.5rem', fontStyle: 'italic' }}>
            * Note: Code fixes are advisory and derived from static error inspection; verify thoroughly in your test suite before committing.
          </div>
        </div>
      )}

      {/* 7. Verification Procedure Card */}
      {verification.how_to_verify && (
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Verification Procedure
          </h3>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
            {verification.how_to_verify}
          </p>
          {verification.expected_behavior && (
            <div style={{ fontSize: '0.85rem', color: 'var(--accent-emerald)', marginBottom: '0.5rem' }}>
              <strong>Expected Behavior:</strong> {verification.expected_behavior}
            </div>
          )}
          {verification.suggested_test_cases && verification.suggested_test_cases.length > 0 && (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <strong>Test Cases:</strong> {verification.suggested_test_cases.join('; ')}
            </div>
          )}
        </div>
      )}

      {/* 8. Confidence & Human Review Alert */}
      <div className="card" style={{
        background: confidence.human_review_required ? 'rgba(245, 158, 11, 0.08)' : 'var(--bg-surface)',
        borderColor: confidence.human_review_required ? 'rgba(245, 158, 11, 0.3)' : 'var(--border-color)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: confidence.human_review_required ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>
            {confidence.human_review_required ? '⚠️ Manual Review Recommended' : '✓ High Confidence Analysis'}
          </span>
          <span className="badge badge-info">{confidence.overall_confidence || 'High'} Overall</span>
        </div>
        {confidence.uncertainty_explanation && (
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {confidence.uncertainty_explanation}
          </p>
        )}
      </div>

      {/* 9. Request Telemetry & Cost Footer */}
      {metrics && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          padding: '0.75rem 1rem',
          background: 'var(--bg-canvas)',
          border: '1px solid var(--border-color)',
          borderRadius: 6,
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
        }}>
          <div>Model: <strong style={{ color: 'var(--accent-cyan)' }}>{metrics.model_used}</strong> {metrics.fallback_used && '(Fallback invoked)'}</div>
          <div>Duration: <strong style={{ color: 'var(--text-primary)' }}>{metrics.total_duration_seconds ? `${metrics.total_duration_seconds}s` : 'N/A'}</strong></div>
          <div>Tokens: Prompt {metrics.prompt_tokens || 0} + Resp {metrics.response_tokens || 0} = <strong style={{ color: 'var(--text-primary)' }}>{metrics.total_tokens || 0}</strong></div>
          {metrics.cost_estimate?.estimated_total_cost_usd !== null && metrics.cost_estimate?.estimated_total_cost_usd !== undefined && (
            <div>Est. Cost: <strong style={{ color: 'var(--accent-emerald)' }}>${metrics.cost_estimate.estimated_total_cost_usd.toFixed(6)}</strong></div>
          )}
        </div>
      )}
    </div>
  );
}

