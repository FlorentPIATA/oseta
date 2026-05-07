export function MacroOverlay() {
  return (
    <div>
      <p style={{ fontSize: '0.6875rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 12 }}>
        Macro Context
      </p>
      <div
        style={{
          height: 260,
          borderRadius: 8,
          border: '1px solid var(--border)',
          background: 'var(--bg-2)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
        }}
      >
        <p style={{ fontSize: '0.875rem', color: 'var(--text-2)', fontWeight: 500 }}>
          ETF + FRED overlay
        </p>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-3)', maxWidth: '28ch', textAlign: 'center', lineHeight: 1.5 }}>
          Requires a <code style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>/data/streams</code> endpoint — coming next.
        </p>
      </div>
      <p style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-3)' }}>
        Will show ETF price trends overlaid with Fed rate and CPI indicators.
      </p>
    </div>
  )
}
