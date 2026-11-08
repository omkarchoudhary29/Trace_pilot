import React, { useEffect, useState } from 'react';
import { fetchEvaluation } from '../services/api';

export default function EvaluationView() {
  const [evalData, setEvalData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchEvaluation()
      .then((res) => {
        setEvalData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted)' }}>Loading benchmark evaluation metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderLeft: '4px solid var(--accent-red)' }}>
        <h3 style={{ color: 'var(--accent-red)', marginBottom: '0.5rem' }}>Failed to load evaluation metrics</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>{error}</p>
      </div>
    );
  }

  if (!evalData || !evalData.available || !evalData.data) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3.5rem 1.5rem' }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📊</div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
          No Benchmark Results Generated Yet
        </h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', maxWidth: 540, margin: '0 auto 1.5rem auto', lineHeight: 1.6 }}>
          TracePilot strictly displays verified mathematical benchmark metrics. Run the Phase 9 evaluation engine to populate this dashboard:
        </p>
        <div className="code-block" style={{ display: 'inline-block', textAlign: 'left', padding: '0.75rem 1.5rem' }}>
          <code>python -m pytest -v tests/test_evaluation_engine.py</code>
        </div>
      </div>
    );
  }

  const { data } = evalData;
  const modelResults = data.model_results || {};
  const modelNames = Object.keys(modelResults);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Overview Card */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Phase 9: Debugging Benchmark Evaluation</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Head-to-head characterization across standardized runtime benchmarks.
            </p>
          </div>
          <span className="badge badge-info">{data.benchmark_version || 'v1.0'}</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div style={{ background: 'var(--bg-card)', padding: '1rem', borderRadius: 6, border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Benchmark Cases</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>{data.benchmark_size || 10}</div>
          </div>
          <div style={{ background: 'var(--bg-card)', padding: '1rem', borderRadius: 6, border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Models Compared</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>{modelNames.length}</div>
          </div>
          <div style={{ background: 'var(--bg-card)', padding: '1rem', borderRadius: 6, border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Evaluation Run ID</div>
            <div style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>{data.run_id}</div>
          </div>
        </div>
      </div>

      {/* Model Comparison Table */}
      <div className="card">
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>
          Head-to-Head Model Performance
        </h3>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Schema Valid %</th>
                <th>Error Type Accuracy</th>
                <th>Category Macro-F1</th>
                <th>Severity Macro-F1</th>
                <th>Grounding Score (1-5)</th>
                <th>Invented Locations</th>
                <th>Mean Latency</th>
              </tr>
            </thead>
            <tbody>
              {modelNames.map((name) => {
                const res = modelResults[name] || {};
                const metrics = res.metrics || {};
                const catM = metrics.category_metrics || {};
                const sevM = metrics.severity_metrics || {};
                const latM = metrics.latency_stats || {};

                return (
                  <tr key={name}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                      {name}
                    </td>
                    <td>{metrics.schema_validation_rate !== undefined ? `${(metrics.schema_validation_rate * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td>{metrics.type_accuracy !== undefined ? `${(metrics.type_accuracy * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td>{catM.macro_f1 !== undefined ? catM.macro_f1.toFixed(2) : 'N/A'}</td>
                    <td>{sevM.macro_f1 !== undefined ? sevM.macro_f1.toFixed(2) : 'N/A'}</td>
                    <td>{metrics.evidence_grounding_mean !== undefined ? `${metrics.evidence_grounding_mean.toFixed(1)} / 5.0` : 'N/A'}</td>
                    <td>{metrics.invented_locations_rate !== undefined ? `${(metrics.invented_locations_rate * 100).toFixed(1)}%` : 'N/A'}</td>
                    <td>{latM.mean_seconds !== undefined ? `${latM.mean_seconds.toFixed(3)}s` : 'N/A'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Token Usage & Cost Table */}
      <div className="card">
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>
          Token Accounting & Verified Cost Estimates
        </h3>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Total Prompt Tokens</th>
                <th>Total Response Tokens</th>
                <th>Total Tokens</th>
                <th>Estimated Cost (USD)</th>
                <th>Pricing Tier Source</th>
              </tr>
            </thead>
            <tbody>
              {modelNames.map((name) => {
                const res = modelResults[name] || {};
                const tstats = res.metrics?.token_stats || {};
                const cost = res.cost_estimate || {};

                return (
                  <tr key={name}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--accent-cyan)' }}>
                      {name}
                    </td>
                    <td>{tstats.total_prompt_tokens ?? 'N/A'}</td>
                    <td>{tstats.total_response_tokens ?? 'N/A'}</td>
                    <td>{tstats.total_tokens ?? 'N/A'}</td>
                    <td style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>
                      {cost.estimated_total_cost_usd !== null && cost.estimated_total_cost_usd !== undefined
                        ? `$${cost.estimated_total_cost_usd.toFixed(6)}`
                        : 'N/A'}
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {cost.pricing_source || 'Unverified'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

