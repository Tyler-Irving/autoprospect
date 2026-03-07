import { useState } from 'react'
import toast from 'react-hot-toast'
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
  const [retrying, setRetrying] = useState(false)

  if (!activeScan) return null

  const { status, progress_pct, businesses_found, businesses_enriched, businesses_scored, label, error_message } = activeScan
  const isFailed = status === 'failed'

  const handleRetry = async () => {
    setRetrying(true)
    try {
      await rerunScan(activeScan.id)
      toast.success('Scan restarted')
    } catch {
      toast.error('Failed to restart scan')
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
        <span className={`text-xs font-mono ${isFailed ? 'text-red-400' : 'text-blue-400'}`}>
          {progress_pct}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full overflow-hidden mb-2" style={{ background: 'var(--secondary)' }}>
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isFailed ? 'bg-red-500' : status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progress_pct}%` }}
        />
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
              className="flex-1 py-1.5 rounded text-xs font-medium bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white transition-colors"
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
