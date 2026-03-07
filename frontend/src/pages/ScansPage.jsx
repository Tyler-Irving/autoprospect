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

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function StatCard({ label, value, sub }) {
  return (
    <div
      className="rounded-xl p-4 md:p-5"
      style={{
        background: 'color-mix(in srgb, var(--card) 86%, #111827 14%)',
        border: '1px solid color-mix(in srgb, var(--border) 80%, #374151 20%)',
      }}
    >
      <p className="text-[11px] uppercase tracking-[0.14em] font-medium mb-1.5" style={{ color: 'var(--muted-foreground)' }}>
        {label}
      </p>
      <p className="text-2xl md:text-[1.75rem] leading-none font-semibold font-mono" style={{ color: 'var(--foreground)' }}>
        {value ?? '—'}
      </p>
      {sub && (
        <p className="text-xs mt-2" style={{ color: 'var(--muted-foreground)' }}>
          {sub}
        </p>
      )}
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
    <div className="flex items-center gap-2 whitespace-nowrap">
      <span className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${colorClass}`} />
      <span className="text-xs capitalize" style={{ color: 'var(--foreground)' }}>{label}</span>
    </div>
  )
}

function buttonBase(disabled) {
  return {
    borderRadius: 10,
    border: '1px solid transparent',
    transition: 'opacity 160ms ease, background-color 160ms ease, border-color 160ms ease',
    opacity: disabled ? 0.45 : 1,
  }
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
  const totalLeads = scans.reduce((sum, s) => sum + (s.lead_count ?? 0), 0)
  const completedScans = scans.filter((s) => s.status === 'completed').length
  const activeScans = scans.filter((s) => !['completed', 'failed'].includes(s.status)).length
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
    <div className="h-full overflow-auto p-4 md:p-6" style={{ background: 'var(--background)' }}>
      <div className="max-w-6xl mx-auto space-y-5">
        <section
          className="relative overflow-hidden rounded-2xl p-5 md:p-6 space-y-5"
          style={{
            background: 'linear-gradient(145deg, color-mix(in srgb, var(--card) 90%, #111827 10%), var(--card))',
            border: '1px solid color-mix(in srgb, var(--border) 82%, #334155 18%)',
          }}
        >
          <div className="absolute -top-20 right-0 w-72 h-72 rounded-full pointer-events-none opacity-70" style={{ background: 'radial-gradient(circle, rgba(249, 115, 22, 0.14), transparent 65%)' }} />
          <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full pointer-events-none opacity-60" style={{ background: 'radial-gradient(circle, rgba(59, 130, 246, 0.12), transparent 65%)' }} />

          <div className="relative flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-[11px] uppercase tracking-[0.16em] font-medium mb-2" style={{ color: 'var(--muted-foreground)' }}>
                Insights
              </p>
              <h1 className="text-xl md:text-2xl font-semibold leading-tight" style={{ color: 'var(--foreground)' }}>
                Scan History
              </h1>
              <p className="text-sm mt-1.5" style={{ color: 'var(--muted-foreground)' }}>
                Review performance, spend, and outcomes across every prospecting run.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className="text-xs px-2.5 py-1 rounded-full"
                style={{
                  color: activeScans > 0 ? '#f59e0b' : 'var(--muted-foreground)',
                  background: activeScans > 0 ? 'color-mix(in srgb, #f59e0b 16%, transparent)' : 'var(--secondary)',
                  border: `1px solid ${activeScans > 0 ? 'color-mix(in srgb, #f59e0b 30%, transparent)' : 'var(--border)'}`,
                }}
              >
                {activeScans > 0 ? `${activeScans} running` : 'No active scans'}
              </span>
            </div>
          </div>

          <div className="relative grid grid-cols-2 xl:grid-cols-4 gap-3">
            <StatCard label="Total Scans" value={scans.length} sub={`${completedScans} completed`} />
            <StatCard label="Businesses Found" value={totalBusinesses} sub={`${totalLeads} promoted to leads`} />
            <StatCard label="This Month" value={`$${(monthCostCents / 100).toFixed(2)}`} sub="Current billing cycle" />
            <StatCard label="All-Time Spend" value={`$${(totalCostCents / 100).toFixed(2)}`} sub="Accumulated API usage" />
          </div>
        </section>

        <section className="rounded-2xl overflow-hidden" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <div className="px-4 md:px-5 py-3.5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--border)' }}>
            <h2 className="text-sm font-medium" style={{ color: 'var(--foreground)' }}>
              Recent Scans
            </h2>
            <button
              onClick={() => navigate('/')}
              className="text-sm px-3 py-1.5 font-medium transition-opacity hover:opacity-90 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-orange-500"
              style={{ ...buttonBase(false), background: '#f97316', color: '#fff', '--tw-ring-offset-color': 'var(--background)' }}
            >
              New Scan
            </button>
          </div>

          {scans.length === 0 ? (
            <div className="px-5 py-16 text-center">
              <div
                className="mx-auto mb-4 w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: 'var(--secondary)', border: '1px solid var(--border)' }}
              >
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ color: 'var(--muted-foreground)' }}>
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 7v5l3 2" />
                </svg>
              </div>
              <p className="text-lg mb-1.5" style={{ color: 'var(--foreground)' }}>No scans yet</p>
              <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
                Run your first scan from the{' '}
                <button
                  onClick={() => navigate('/')}
                  className="hover:underline cursor-pointer"
                  style={{ color: '#f97316' }}
                >
                  Map
                </button>{' '}
                page.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[920px]">
                <thead>
                  <tr className="text-left" style={{ borderBottom: '1px solid var(--border)' }}>
                    <th className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'var(--muted-foreground)' }}>Status</th>
                    <th className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'var(--muted-foreground)' }}>Label</th>
                    <th className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'var(--muted-foreground)' }}>Created</th>
                    <th className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'var(--muted-foreground)' }}>Businesses</th>
                    <th className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'var(--muted-foreground)' }}>Leads</th>
                    <th className="px-4 py-3 text-[11px] font-medium uppercase tracking-[0.12em]" style={{ color: 'var(--muted-foreground)' }}>Cost</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: 'var(--border)' }}>
                  {scans.map((scan) => (
                    <tr
                      key={scan.id}
                      className="transition-colors hover:bg-[#141414]"
                    >
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
                        <div>{relativeDate(scan.created_at)}</div>
                        <div className="text-[11px] mt-0.5">{formatDate(scan.created_at)}</div>
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap" style={{ color: 'var(--muted-foreground)' }}>
                        {scan.businesses_found ?? 0} found · {scan.businesses_scored ?? 0} scored
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap">
                        <span style={{ color: (scan.lead_count ?? 0) > 0 ? 'var(--foreground)' : 'var(--muted-foreground)' }}>
                          {scan.lead_count ?? 0} leads
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap font-mono" style={{ color: 'var(--muted-foreground)' }}>
                        ${((scan.api_cost_cents ?? 0) / 100).toFixed(2)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="ml-auto grid grid-cols-3 gap-2 w-[282px]">
                          {scan.status === 'completed' && (
                            <button
                              onClick={() => handleViewOnMap(scan)}
                              className="h-8 w-full text-xs px-3 inline-flex items-center justify-center font-medium hover:opacity-90 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-orange-500"
                              style={{
                                ...buttonBase(false),
                                background: 'var(--secondary)',
                                color: 'var(--foreground)',
                                borderColor: 'var(--border)',
                                '--tw-ring-offset-color': 'var(--background)',
                              }}
                            >
                              View map
                            </button>
                          )}
                          {scan.status !== 'completed' && (
                            <span className="h-8 w-full" aria-hidden="true" />
                          )}
                          <button
                            onClick={() => handleRerun(scan)}
                            disabled={!!rerunning[scan.id]}
                            className="h-8 w-full text-xs px-3 inline-flex items-center justify-center font-medium hover:opacity-90 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-orange-500"
                            style={{
                              ...buttonBase(!!rerunning[scan.id]),
                              background: '#f97316',
                              color: '#fff',
                              borderColor: 'color-mix(in srgb, #ea580c 55%, transparent)',
                              '--tw-ring-offset-color': 'var(--background)',
                            }}
                          >
                            {rerunning[scan.id] ? 'Running' : 'Rerun'}
                          </button>
                          <button
                            onClick={() => handleDelete(scan)}
                            disabled={!!deleting[scan.id]}
                            className="h-8 w-full text-xs px-3 inline-flex items-center justify-center font-medium hover:opacity-90 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-red-500"
                            style={{
                              ...buttonBase(!!deleting[scan.id]),
                              background: 'color-mix(in srgb, #ef4444 14%, transparent)',
                              color: '#fca5a5',
                              borderColor: 'color-mix(in srgb, #ef4444 35%, transparent)',
                              '--tw-ring-offset-color': 'var(--background)',
                            }}
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
        </section>
      </div>
    </div>
  )
}
