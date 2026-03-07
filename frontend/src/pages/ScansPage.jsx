import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToasts } from '@/components/ui/toast'
import { useScanStore } from '../store/scanStore'

function relativeDate(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-lg p-4" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <p className="text-xs uppercase tracking-wide font-medium mb-1" style={{ color: 'var(--muted-foreground)' }}>{label}</p>
      <p className="text-2xl font-bold" style={{ color: 'var(--foreground)' }}>{value ?? '—'}</p>
    </div>
  )
}

function StatusDot({ status }) {
  const colorClass =
    status === 'completed'
      ? 'bg-green-400'
      : status === 'failed'
      ? 'bg-red-400'
      : 'bg-yellow-400'

  const label =
    status === 'completed'
      ? 'Completed'
      : status === 'failed'
      ? 'Failed'
      : status === 'discovering'
      ? 'Discovering'
      : status === 'enriching_t1'
      ? 'Enriching'
      : status === 'scoring_t1'
      ? 'Scoring'
      : status === 'pending'
      ? 'Pending'
      : status

  return (
    <div className="flex items-center gap-1.5 whitespace-nowrap">
      <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${colorClass}`} />
      <span className="text-xs capitalize" style={{ color: 'var(--foreground)' }}>{label}</span>
    </div>
  )
}

export default function ScansPage() {
  const { scans, loadScans, deleteScan, rerunScan, loadScanOnMap } = useScanStore()
  const toasts = useToasts()
  const navigate = useNavigate()
  const [deleting, setDeleting] = useState({})
  const [rerunning, setRerunning] = useState({})

  useEffect(() => {
    loadScans()
  }, [])

  const now = new Date()
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)

  const totalBusinesses = scans.reduce((sum, s) => sum + (s.businesses_found ?? 0), 0)
  const totalCostCents = scans.reduce((sum, s) => sum + (s.api_cost_cents ?? 0), 0)
  const monthCostCents = scans
    .filter((s) => new Date(s.created_at) >= monthStart)
    .reduce((sum, s) => sum + (s.api_cost_cents ?? 0), 0)

  const handleViewOnMap = (scan) => {
    loadScanOnMap(scan)
    navigate('/')
  }

  const handleRerun = async (scan) => {
    setRerunning((prev) => ({ ...prev, [scan.id]: true }))
    try {
      await rerunScan(scan.id)
      navigate('/')
    } catch {
      toasts.error('Failed to re-run scan')
      setRerunning((prev) => ({ ...prev, [scan.id]: false }))
    }
  }

  const handleDelete = async (scan) => {
    const message =
      scan.lead_count > 0
        ? `This scan has ${scan.lead_count} lead(s). Deleting it will permanently remove those leads too. Continue?`
        : 'Delete this scan?'

    if (!window.confirm(message)) return

    setDeleting((prev) => ({ ...prev, [scan.id]: true }))
    try {
      await deleteScan(scan.id)
      toasts.success('Scan deleted')
    } catch {
      toasts.error('Failed to delete scan')
      setDeleting((prev) => ({ ...prev, [scan.id]: false }))
    }
  }

  return (
    <div className="h-full overflow-auto p-6" style={{ background: 'var(--background)' }}>
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold" style={{ color: 'var(--foreground)' }}>Scan History</h1>
          <button
            onClick={() => navigate('/')}
            className="text-sm px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
          >
            New Scan
          </button>
        </div>

        {/* Stats bar */}
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Total Scans" value={scans.length} />
          <StatCard label="Businesses Found" value={totalBusinesses} />
          <StatCard label="This Month" value={`$${(monthCostCents / 100).toFixed(2)}`} />
          <StatCard label="All-Time Spend" value={`$${(totalCostCents / 100).toFixed(2)}`} />
        </div>

        {/* Scan list */}
        {scans.length === 0 ? (
          <div className="text-center py-16" style={{ color: 'var(--muted-foreground)' }}>
            <p className="text-lg mb-2">No scans yet</p>
            <p className="text-sm">
              Run your first scan from the{' '}
              <button
                onClick={() => navigate('/')}
                className="hover:underline"
                style={{ color: '#f97316' }}
              >
                Map
              </button>{' '}
              page.
            </p>
          </div>
        ) : (
          <div className="rounded-xl overflow-hidden" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left" style={{ borderBottom: '1px solid var(--border)' }}>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--muted-foreground)' }}>Status</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--muted-foreground)' }}>Label</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--muted-foreground)' }}>Date</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--muted-foreground)' }}>Businesses</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--muted-foreground)' }}>Leads</th>
                  <th className="px-4 py-3 text-xs font-medium uppercase tracking-wide" style={{ color: 'var(--muted-foreground)' }}>Cost</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border)' }}>
                {scans.map((scan) => (
                  <tr key={scan.id} className="hover:bg-[#1a1a1a] transition-colors">
                    <td className="px-4 py-3">
                      <StatusDot status={scan.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-medium leading-snug" style={{ color: 'var(--foreground)' }}>
                        {scan.label || 'Unnamed scan'}
                      </div>
                      {scan.place_types?.length > 0 && (
                        <div className="text-xs mt-0.5 capitalize" style={{ color: 'var(--muted-foreground)' }}>
                          {scan.place_types.join(', ')}
                        </div>
                      )}
                    </td>
                    <td
                      className="px-4 py-3 text-xs whitespace-nowrap"
                      style={{ color: 'var(--muted-foreground)' }}
                      title={new Date(scan.created_at).toLocaleString()}
                    >
                      {relativeDate(scan.created_at)}
                    </td>
                    <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: 'var(--muted-foreground)' }}>
                      {scan.businesses_found ?? 0} found &middot; {scan.businesses_scored ?? 0} scored
                    </td>
                    <td className="px-4 py-3 text-xs whitespace-nowrap">
                      <span style={{ color: (scan.lead_count ?? 0) > 0 ? 'var(--foreground)' : 'var(--muted-foreground)' }}>
                        {scan.lead_count ?? 0} leads
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: 'var(--muted-foreground)' }}>
                      ${((scan.api_cost_cents ?? 0) / 100).toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1.5 flex-nowrap">
                        {scan.status === 'completed' && (
                          <button
                            onClick={() => handleViewOnMap(scan)}
                            className="text-xs px-2 py-1 rounded hover:bg-[#333] transition-colors"
                            style={{ background: 'var(--secondary)', color: 'var(--foreground)' }}
                          >
                            View on Map
                          </button>
                        )}
                        <button
                          onClick={() => handleRerun(scan)}
                          disabled={!!rerunning[scan.id]}
                          className="text-xs px-2 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 transition-colors"
                        >
                          {rerunning[scan.id] ? 'Running…' : 'Re-run'}
                        </button>
                        <button
                          onClick={() => handleDelete(scan)}
                          disabled={!!deleting[scan.id]}
                          className="text-xs px-2 py-1 rounded bg-red-900/50 hover:bg-red-800/60 text-red-400 disabled:opacity-40 transition-colors"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
