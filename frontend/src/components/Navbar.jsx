import React from 'react';

export default function Navbar({ activeTab, setActiveTab, health }) {
  return (
    <header style={{
      borderBottom: '1px solid var(--border-color)',
      background: 'rgba(17, 24, 39, 0.85)',
      backdropFilter: 'blur(10px)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      padding: '0.875rem 1.5rem'
    }}>
      <div style={{
        maxWidth: 1400,
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
          <div style={{
            width: 34,
            height: 34,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #38bdf8 0%, #6366f1 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '1.1rem',
            color: '#0f172a'
          }}>
            T
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.02em', color: '#fff' }}>
              TracePilot
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Error & Log Intelligence Platform
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav style={{ display: 'flex', gap: '0.5rem', background: 'var(--bg-canvas)', padding: '0.25rem', borderRadius: 8, border: '1px solid var(--border-color)' }}>
          <button
            onClick={() => setActiveTab('debugger')}
            style={{
              background: activeTab === 'debugger' ? 'var(--bg-card)' : 'transparent',
              color: activeTab === 'debugger' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              border: 'none',
              padding: '0.4rem 1rem',
              borderRadius: 6,
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Debugger Dashboard
          </button>
          <button
            onClick={() => setActiveTab('evaluation')}
            style={{
              background: activeTab === 'evaluation' ? 'var(--bg-card)' : 'transparent',
              color: activeTab === 'evaluation' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              border: 'none',
              padding: '0.4rem 1rem',
              borderRadius: 6,
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            Evaluation Lab
          </button>
        </nav>

        {/* System Meta */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            background: 'var(--bg-card)',
            padding: '0.35rem 0.65rem',
            borderRadius: 6,
            border: '1px solid var(--border-color)'
          }}>
            <span style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: health?.status === 'ok' ? '#10b981' : '#ef4444'
            }}></span>
            <span>{health?.primary_model || 'gemini-3.5-flash-lite'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}

