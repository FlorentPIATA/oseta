import { CorrelationHeatmap } from './components/heatmap/CorrelationHeatmap'
import { LeadGraph }          from './components/LeadGraph'
import { MacroOverlay }       from './components/MacroOverlay'
import { PipelinePanel }      from './components/PipelinePanel'
import { SignalFeed }         from './components/SignalFeed'
import { SignalOfTheDay }     from './components/SignalOfTheDay'
import { TrackRecord }        from './components/TrackRecord'

const S = {
  page:    { minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-1)' } as const,
  header:  { borderBottom: '1px solid var(--border)', padding: '0 40px', height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between' } as const,
  main:    { maxWidth: 1080, margin: '0 auto', padding: '0 40px 80px' } as const,
  section: { padding: '40px 0 0' } as const,
  cols:    { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 } as const,
}

export default function App() {
  return (
    <div style={S.page}>

      {/* Header */}
      <header style={S.header}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
          <span style={{ fontWeight: 600, fontSize: '0.9375rem', letterSpacing: '-0.01em', color: 'var(--text-1)' }}>
            OSETA
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-3)' }}>
            Observatory for Strategic Emerging Technologies &amp; Analytics
          </span>
        </div>
        <span style={{ fontSize: '0.6875rem', fontFamily: 'monospace', color: 'var(--text-3)', padding: '2px 8px', border: '1px solid var(--border)', borderRadius: 4 }}>
          v0.1.0
        </span>
      </header>

      {/* Admin */}
      <PipelinePanel />

      <main style={S.main}>

        {/* 1 — Signal of the Day */}
        <SignalOfTheDay />

        {/* 2 + 3 — Lead Graph + Macro Overlay */}
        <div style={{ ...S.section }}>
          <div style={S.cols}>
            <LeadGraph />
            <MacroOverlay />
          </div>
        </div>

        {/* 4 — Heatmap */}
        <div style={S.section}>
          <p style={{ fontSize: '0.6875rem', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 16 }}>
            Correlation Matrix
          </p>
          <CorrelationHeatmap />
        </div>

        {/* 5 — Signal Feed */}
        <div style={{ ...S.section, paddingTop: 48 }}>
          <SignalFeed />
        </div>

        {/* 6 — Track Record */}
        <div style={{ ...S.section, paddingTop: 48 }}>
          <TrackRecord />
        </div>

      </main>
    </div>
  )
}
