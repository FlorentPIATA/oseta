import { usePredictions, useTrackRecord } from '../hooks/usePredictions'
import type { Prediction } from '../types/predictions'

const STATUS_STYLE: Record<string, { label: string; color: string }> = {
  realized: { label: 'Realized',  color: 'var(--pos)' },
  partial:  { label: 'Partial',   color: 'var(--accent)' },
  failed:   { label: 'Failed',    color: 'var(--neg)' },
  pending:  { label: 'Pending',   color: 'var(--text-3)' },
}

const primaryLabel: React.CSSProperties = {
  fontSize: '0.8125rem',
  fontWeight: 600,
  color: 'var(--text-1)',
  borderLeft: '2px solid var(--accent)',
  paddingLeft: 10,
  marginBottom: 20,
}

function AccuracyRing({ pct }: { pct: number }) {
  const r = 30
  const circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ

  return (
    <svg width={80} height={80} viewBox="0 0 80 80" role="img" aria-label={`Accuracy: ${pct}%`}>
      <circle cx={40} cy={40} r={r} fill="none" stroke="var(--bg-3)" strokeWidth={6} />
      <circle
        cx={40} cy={40} r={r} fill="none"
        stroke={pct >= 70 ? 'var(--pos)' : pct >= 50 ? 'var(--accent)' : 'var(--neg)'}
        strokeWidth={6}
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 40 40)"
        style={{ transition: 'stroke-dasharray 0.6s ease-out' }}
      />
      <text x={40} y={44} textAnchor="middle" fontSize={14} fontWeight={600} fill="var(--text-1)" fontFamily="monospace" className="stat">
        {pct}%
      </text>
    </svg>
  )
}

function PredictionRow({ p }: { p: Prediction }) {
  const s = STATUS_STYLE[p.status] ?? STATUS_STYLE.pending
  const date = new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const dir = p.predicted_direction.toLowerCase()

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 12, alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: '0.8125rem' }}>
      <div>
        <span style={{ color: 'var(--text-1)', fontWeight: 500, fontFamily: 'monospace' }}>
          {p.sector_code ?? `#${p.sector_id}`}
          {p.linked_sector_code ? ` × ${p.linked_sector_code}` : p.linked_sector_id ? ` × #${p.linked_sector_id}` : ''}
        </span>
        <span style={{ color: 'var(--text-3)', marginLeft: 8 }}>
          {dir} · {p.horizon_days}d horizon
        </span>
      </div>
      <span style={{ fontFamily: 'monospace', color: 'var(--text-3)', fontSize: '0.75rem' }} className="stat">
        {date}
      </span>
      <span style={{ fontSize: '0.75rem', fontWeight: 500, color: s.color, minWidth: 56, textAlign: 'right' }}>
        {s.label}
      </span>
    </div>
  )
}

export function TrackRecord() {
  const { data: tr, isLoading: trLoading } = useTrackRecord()
  const { data: preds, isLoading: predsLoading } = usePredictions(10)

  const isLoading = trLoading || predsLoading
  const pct = tr?.accuracy != null ? Math.round(tr.accuracy * 100) : null

  return (
    <section>
      <p style={primaryLabel}>Track Record</p>

      {isLoading && (
        <div className="animate-pulse" style={{ height: 96, borderRadius: 4, background: 'var(--bg-3)' }} />
      )}

      {!isLoading && tr && (
        <div style={{ display: 'flex', gap: 32, alignItems: 'center', marginBottom: 28, flexWrap: 'wrap' }}>
          {pct != null ? (
            <AccuracyRing pct={pct} />
          ) : (
            <div style={{ width: 80, height: 80, borderRadius: '50%', border: '6px solid var(--bg-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', color: 'var(--text-3)', textAlign: 'center', lineHeight: 1.3 }}>
              No data yet
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'auto auto', gap: '6px 24px', fontSize: '0.8125rem' }}>
            {[
              { label: 'Total predictions', val: tr.total },
              { label: 'Realized',          val: tr.realized },
              { label: 'Partial',           val: tr.partial },
              { label: 'Failed',            val: tr.failed },
              { label: 'Pending',           val: tr.pending },
            ].map(({ label, val }) => (
              <>
                <span key={`l-${label}`} style={{ color: 'var(--text-3)' }}>{label}</span>
                <span key={`v-${label}`} style={{ color: 'var(--text-1)', fontWeight: 500, fontFamily: 'monospace', textAlign: 'right' }} className="stat">{val}</span>
              </>
            ))}
          </div>
        </div>
      )}

      {!isLoading && !tr?.total && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ color: 'var(--text-3)', fontSize: '0.875rem', marginBottom: 8 }}>
            No predictions yet.
          </p>
          <button
            onClick={() => document.getElementById('admin')?.scrollIntoView({ behavior: 'smooth' })}
            style={{ fontSize: '0.8125rem', color: 'var(--accent)', background: 'none', border: 'none', padding: 0, cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: 3 }}
          >
            Run pipeline →
          </button>
        </div>
      )}

      {!isLoading && !!preds?.length && (
        <div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-3)', marginBottom: 8, fontWeight: 500 }}>
            Last {preds.length} predictions
          </p>
          {preds.map(p => <PredictionRow key={p.id} p={p} />)}
        </div>
      )}
    </section>
  )
}
