import { useEffect, useRef, useState } from 'react'
import { fetchPipelineStatus, triggerRefresh } from '../api/correlations'
import type { PipelineStatus } from '../types/correlation'

const STEPS: { key: PipelineStatus['step']; label: string }[] = [
  { key: 'fetching_etfs', label: 'Fetch ETF prices' },
  { key: 'fetching_fred', label: 'Fetch FRED macro' },
  { key: 'computing',     label: 'Compute correlations' },
  { key: 'predicting',    label: 'Generate predictions' },
]

function stepIndex(step: PipelineStatus['step']): number {
  return STEPS.findIndex(s => s.key === step)
}

export function PipelinePanel() {
  const [open, setOpen]           = useState(false)
  const [masterKey, setMasterKey] = useState('')
  const [status, setStatus]       = useState<PipelineStatus | null>(null)
  const [triggering, setTriggering] = useState(false)
  const [keyError, setKeyError]   = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const poll = (key: string) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const s = await fetchPipelineStatus(key)
        setStatus(s)
        if (s.status !== 'running') stopPolling()
      } catch { stopPolling() }
    }, 5000)
  }

  useEffect(() => () => stopPolling(), [])

  const handleRun = async () => {
    if (!masterKey) return
    setKeyError(null)
    setTriggering(true)
    try {
      const res = await triggerRefresh(masterKey)
      const s = await fetchPipelineStatus(masterKey)
      setStatus(s)
      if (res.status === 'started' || res.status === 'already_running') poll(masterKey)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('403')) setKeyError('Invalid master key')
      else setKeyError(msg)
    } finally {
      setTriggering(false)
    }
  }

  const isRunning     = status?.status === 'running' || triggering
  const currentStepIdx = stepIndex(status?.step ?? null)

  return (
    <div className="border-b border-gray-800/60">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full px-8 py-2 flex items-center gap-2 text-xs text-gray-600 hover:text-gray-500 transition-colors"
      >
        <span>⚙ Admin</span>
        <span className="ml-auto opacity-50">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <div className="px-8 pb-5 pt-3 bg-gray-950/50 border-t border-gray-800/40">
          <div className="max-w-md flex flex-col gap-4">

            {/* Controls */}
            <div className="flex gap-2">
              <input
                type="password"
                placeholder="Master key"
                value={masterKey}
                onChange={e => { setMasterKey(e.target.value); setKeyError(null) }}
                onKeyDown={e => e.key === 'Enter' && handleRun()}
                className="flex-1 bg-gray-900 border border-gray-800 rounded px-3 py-1.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-gray-600"
              />
              <button
                onClick={handleRun}
                disabled={!masterKey || isRunning}
                className="px-4 py-1.5 rounded bg-blue-700 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-medium text-white transition-colors whitespace-nowrap"
              >
                {isRunning ? 'Running…' : 'Run Pipeline'}
              </button>
            </div>

            {keyError && (
              <p className="text-xs text-red-500">{keyError}</p>
            )}

            {/* Step indicators */}
            {status && (
              <div className="flex flex-col gap-2.5">
                {STEPS.map((step, i) => {
                  const done   = status.status === 'success'
                              || ((status.status === 'running' || status.status === 'error') && currentStepIdx > i)
                  const active = status.status === 'running' && currentStepIdx === i
                  const failed = status.status === 'error'   && currentStepIdx === i

                  const metric = done
                    ? (i === 0 ? (status.etf_new    != null ? `${status.etf_new} new pts`     : null) : null)
                      ?? (i === 1 ? (status.fred_new  != null ? `${status.fred_new} new pts`   : null) : null)
                      ?? (i === 2 ? (status.computed  != null ? `${status.computed} pairs`     : null) : null)
                      ?? (i === 3 ? (status.predictions != null ? `${status.predictions} new`  : null) : null)
                    : null

                  return (
                    <div key={step.key} className="flex items-center gap-3 text-sm">
                      <span className={`w-4 text-center font-mono text-xs ${
                        done   ? 'text-green-400' :
                        active ? 'text-blue-400 animate-pulse' :
                        failed ? 'text-red-400' : 'text-gray-700'
                      }`}>
                        {done ? '✓' : active ? '●' : failed ? '✗' : '○'}
                      </span>
                      <span className={
                        done   ? 'text-gray-300' :
                        active ? 'text-white font-medium' :
                        failed ? 'text-red-400' : 'text-gray-600'
                      }>
                        {step.label}
                      </span>
                      {metric && (
                        <span className="ml-auto text-xs text-gray-500 font-mono">{metric}</span>
                      )}
                    </div>
                  )
                })}

                {status.status === 'success' && status.finished_at && (
                  <p className="text-xs text-green-600 pt-1">
                    Completed · {new Date(status.finished_at).toUTCString()}
                  </p>
                )}
                {status.status === 'error' && (
                  <p className="text-xs text-red-500 pt-1">{status.error ?? 'Unknown error'}</p>
                )}
                {status.status === 'running' && (
                  <p className="text-xs text-gray-600 pt-1">
                    ETF fetch takes ~2 min (Alpha Vantage rate limit)
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
