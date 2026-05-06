import { CorrelationHeatmap } from './components/heatmap/CorrelationHeatmap'
import { InsightCard } from './components/InsightCard'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-8 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">OSETA</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Observatory for Strategic Emerging Technologies &amp; Analytics
          </p>
        </div>
        <span className="text-xs font-mono text-gray-600 bg-gray-900 px-3 py-1 rounded-full border border-gray-800">
          v0.1.0 · MVP
        </span>
      </header>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-8 py-8 flex flex-col gap-6">
        <div>
          <h2 className="text-lg font-semibold text-white">Cross-Sector Correlation Matrix</h2>
          <p className="text-sm text-gray-400 mt-1">
            SPDR ETF price correlations over a rolling window. Green = positive, red = negative.
            Lag indicates how many days one sector leads the other.
          </p>
        </div>

        <InsightCard />
        <CorrelationHeatmap />
      </main>
    </div>
  )
}
