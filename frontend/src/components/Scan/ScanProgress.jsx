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
  const { activeScan } = useScanStore()

  if (!activeScan) return null

  const { status, progress_pct, businesses_found, businesses_enriched, businesses_scored, label, error_message } = activeScan
  const isTerminal = status === 'completed' || status === 'failed'

  return (
    <div className="mt-3 p-3 rounded" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium truncate" style={{ color: 'var(--foreground)' }}>{label || 'Scan in progress'}</span>
        <span className={`text-xs font-mono ${status === 'failed' ? 'text-red-400' : 'text-blue-400'}`}>
          {progress_pct}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full overflow-hidden mb-2" style={{ background: 'var(--secondary)' }}>
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            status === 'failed' ? 'bg-red-500' : status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progress_pct}%` }}
        />
      </div>

      <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>{STATUS_LABELS[status] || status}</p>

      {/* Counters */}
      {businesses_found > 0 && (
        <div className="flex gap-3 mt-2 text-xs" style={{ color: 'var(--muted-foreground)' }}>
          <span style={{ color: 'var(--foreground)' }}>{businesses_found} found</span>
          {businesses_enriched > 0 && <span>{businesses_enriched} enriched</span>}
          {businesses_scored > 0 && <span>{businesses_scored} scored</span>}
        </div>
      )}

      {status === 'failed' && error_message && (
        <p className="mt-2 text-xs text-red-400 truncate">{error_message}</p>
      )}
    </div>
  )
}
