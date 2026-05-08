import { CorrelationHeatmap } from './components/heatmap/CorrelationHeatmap'
import { LeadGraph }          from './components/LeadGraph'
import { MacroOverlay }       from './components/MacroOverlay'
import { PipelinePanel }      from './components/PipelinePanel'
import { SectionNav }         from './components/SectionNav'
import { SignalFeed }         from './components/SignalFeed'
import { SignalOfTheDay }     from './components/SignalOfTheDay'
import { TrackRecord }        from './components/TrackRecord'

function GearIcon() {
  return (
    <svg width={15} height={15} viewBox="0 0 15 15" fill="none" stroke="currentColor" strokeWidth={1.5} aria-hidden>
      <circle cx={7.5} cy={7.5} r={2} />
      <path d="M7.5 1v1.5M7.5 12.5V14M1 7.5h1.5M12.5 7.5H14M2.93 2.93l1.06 1.06M11.01 11.01l1.06 1.06M2.93 12.07l1.06-1.06M11.01 3.99l1.06-1.06" strokeLinecap="round" />
    </svg>
  )
}

export default function App() {
  const scrollToAdmin = () => {
    document.getElementById('admin')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-1)]">

      <header className="h-[52px] flex items-center justify-between px-10 border-b border-[var(--border)]">
        <div className="flex items-baseline gap-3">
          <span className="font-semibold text-[0.9375rem] tracking-tight text-[var(--text-1)]">
            OSETA
          </span>
          <span className="text-xs text-[var(--text-3)]">
            Observatory for Strategic Emerging Technologies &amp; Analytics
          </span>
        </div>
        <button
          onClick={scrollToAdmin}
          aria-label="Open admin panel"
          className="flex items-center justify-center w-8 h-8 rounded-md border border-[var(--border)] bg-transparent text-[var(--text-3)] cursor-pointer hover:text-[var(--text-2)] hover:border-[var(--text-3)] transition-colors"
        >
          <GearIcon />
        </button>
      </header>

      <SectionNav />

      <main className="max-w-[1080px] mx-auto px-5 md:px-10 pb-20">

        <div id="signal" className="scroll-mt-[44px]">
          <SignalOfTheDay />
        </div>

        <div id="graph" className="pt-10 scroll-mt-[44px]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <LeadGraph />
            <MacroOverlay />
          </div>
        </div>

        <div id="heatmap" className="pt-10 scroll-mt-[44px]">
          <p className="text-[0.6875rem] font-semibold tracking-[0.08em] uppercase text-[var(--text-3)] mb-4">
            Correlation Matrix
          </p>
          <CorrelationHeatmap />
        </div>

        <div id="signals" className="pt-12 scroll-mt-[44px]">
          <SignalFeed />
        </div>

        <div id="predictions" className="pt-12 scroll-mt-[44px]">
          <TrackRecord />
        </div>

      </main>

      <div id="admin">
        <PipelinePanel />
      </div>

    </div>
  )
}
