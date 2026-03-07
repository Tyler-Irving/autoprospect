import { useState } from 'react'
import { useToasts } from '@/components/ui/toast'
import { useScanStore } from '../../store/scanStore'

const STATUS_LABELS = {
  pending: 'Starting…',
  discovering: 'Discovering businesses…',
  enriching_t1: 'Enriching websites…',
  scoring_t1: 'Scoring with AI…',
  completed: 'Complete',
  failed: 'Failed',
}

export default function ScanProgress() {
  const { activeScan, setActiveScan, rerunScan } = useScanStore()
  const toasts = useToasts()
  const [retrying, setRetrying] = useState(false)

  if (!activeScan) return null

  const { status, progress_pct, businesses_found, businesses_enriched, businesses_scored, label, error_message, api_cost_cents } = activeScan
  const isFailed = status === 'failed'

  const handleRetry = async () => {
    setRetrying(true)
    try {
      await rerunScan(activeScan.id)
      toasts.success('Scan restarted')
    } catch {
      toasts.error('Failed to restart scan')
    } finally {
      setRetrying(false)
    }
  }

  const handleDismiss = () => setActiveScan(null)

  return (
    <div
      className="mt-3 p-3 rounded"
      style={{
        background: isFailed ? 'rgba(239,68,68,0.08)' : 'var(--card)',
        border: `1px solid ${isFailed ? 'rgba(239,68,68,0.4)' : 'var(--border)'}`,
      }}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium truncate" style={{ color: 'var(--foreground)' }}>{label || 'Scan in progress'}</span>
        <span
          className="text-xs font-mono"
          style={{ color: isFailed ? '#f87171' : status === 'completed' ? '#22c55e' : '#f97316' }}
        >
          {progress_pct}%
        </span>
      </div>

      {/* Status pill (replaces progress bar) */}
      <div className="mb-2">
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium"
          style={{
            color: isFailed ? '#fca5a5' : status === 'completed' ? '#86efac' : '#fdba74',
            background: isFailed
              ? 'color-mix(in srgb, #ef4444 14%, transparent)'
              : status === 'completed'
              ? 'color-mix(in srgb, #22c55e 14%, transparent)'
              : 'color-mix(in srgb, #f97316 14%, transparent)',
            border: `1px solid ${
              isFailed
                ? 'color-mix(in srgb, #ef4444 34%, transparent)'
                : status === 'completed'
                ? 'color-mix(in srgb, #22c55e 34%, transparent)'
                : 'color-mix(in srgb, #f97316 34%, transparent)'
            }`,
          }}
        >
          {status === 'completed' ? (
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
              <path d="M20 6 9 17l-5-5" />
            </svg>
          ) : (
            <span
              className="w-2.5 h-2.5 rounded-full border-2 border-current animate-spin"
              style={{ borderTopColor: 'transparent' }}
              aria-hidden="true"
            />
          )}
          {status === 'completed' ? 'Done' : isFailed ? 'Stopped' : 'Running'}
        </span>
      </div>

      <p className="text-xs" style={{ color: isFailed ? '#f87171' : 'var(--muted-foreground)' }}>
        {STATUS_LABELS[status] || status}
      </p>

      {/* Counters */}
      {businesses_found > 0 && (
        <div className="flex gap-3 mt-2 text-xs" style={{ color: 'var(--muted-foreground)' }}>
          <span style={{ color: 'var(--foreground)' }}>{businesses_found} found</span>
          {businesses_enriched > 0 && <span>{businesses_enriched} enriched</span>}
          {businesses_scored > 0 && <span>{businesses_scored} scored</span>}
          {api_cost_cents > 0 && (
            <span className="ml-auto font-mono">${(api_cost_cents / 100).toFixed(2)}</span>
          )}
        </div>
      )}

      {/* Error detail + actions */}
      {isFailed && (
        <div className="mt-3">
          {error_message && (
            <p className="text-xs text-red-400 mb-3 leading-relaxed break-words">{error_message}</p>
          )}
          <div className="flex gap-2">
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="flex-1 py-1.5 rounded text-xs font-medium disabled:opacity-50 text-white transition-all"
            style={{ background: '#f97316' }}
            >
              {retrying ? 'Restarting…' : 'Retry Scan'}
            </button>
            <button
              onClick={handleDismiss}
              className="px-3 py-1.5 rounded text-xs font-medium transition-colors"
              style={{ background: 'var(--secondary)', color: 'var(--muted-foreground)' }}
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
