import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLeadStore } from '../store/leadStore'
import { scansApi } from '../api/scans'
import { getScoreColor, getScoreLabel } from '../utils/constants'
import toast from 'react-hot-toast'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'new', label: 'New' },
  { value: 'researching', label: 'Researching' },
  { value: 'outreach_ready', label: 'Outreach Ready' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'follow_up', label: 'Follow Up' },
  { value: 'responded', label: 'Responded' },
  { value: 'meeting_booked', label: 'Meeting Booked' },
  { value: 'proposal_sent', label: 'Proposal Sent' },
  { value: 'won', label: 'Won' },
  { value: 'lost', label: 'Lost' },
]

const STATUS_COLORS = {
  new: 'bg-slate-700 text-slate-300',
  researching: 'bg-blue-900/50 text-blue-300',
  outreach_ready: 'bg-indigo-900/50 text-indigo-300',
  contacted: 'bg-yellow-900/50 text-yellow-300',
  follow_up: 'bg-orange-900/50 text-orange-300',
  responded: 'bg-cyan-900/50 text-cyan-300',
  meeting_booked: 'bg-green-900/50 text-green-300',
  proposal_sent: 'bg-purple-900/50 text-purple-300',
  won: 'bg-green-800/60 text-green-200',
  lost: 'bg-red-900/50 text-red-300',
  not_interested: 'bg-slate-800 text-slate-500',
}

const PRIORITY_COLORS = {
  low: 'text-slate-500',
  medium: 'text-yellow-400',
  high: 'text-orange-400',
  urgent: 'text-red-400',
}

function StatCard({ label, value, sub }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl px-5 py-4">
      <p className="text-xs text-slate-500 uppercase tracking-wide font-medium mb-1">{label}</p>
      <p className="text-2xl font-bold text-white">{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-500 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function LeadsPage() {
  const { leads, filters, isLoading, setFilters, fetchLeads, updateLead, deleteLead } = useLeadStore()
  const [stats, setStats] = useState(null)
  const isMounted = useRef(false)

  useEffect(() => {
    fetchLeads()
    scansApi.dashboardStats().then(({ data }) => setStats(data)).catch(() => {})
  }, [])

  useEffect(() => {
    // Skip the first run — the mount effect above already fetches leads.
    if (!isMounted.current) {
      isMounted.current = true
      return
    }
    fetchLeads()
  }, [filters.status, filters.minScore])

  const handleStatusChange = async (leadId, newStatus) => {
    try {
      await updateLead(leadId, { outreach_status: newStatus })
    } catch {
      toast.error('Failed to update status')
    }
  }

  return (
    <div className="h-full overflow-auto bg-slate-950 p-6">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-semibold text-slate-100">Lead Pipeline</h1>
          <span className="text-sm text-slate-500">{leads.length} lead{leads.length !== 1 ? 's' : ''}</span>
        </div>

        {/* Stats row */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <StatCard label="Total Leads" value={stats.total_leads} />
            <StatCard
              label="Avg AI Score"
              value={stats.avg_automation_score ?? '—'}
              sub="Tier 1"
            />
            <StatCard
              label="Contacted"
              value={(stats.leads_by_status?.contacted ?? 0) + (stats.leads_by_status?.follow_up ?? 0)}
              sub="contacted + follow-up"
            />
            <StatCard
              label="Monthly Cost"
              value={`$${((stats.monthly_api_cost_cents ?? 0) / 100).toFixed(2)}`}
              sub={`${stats.scans_this_month} scans this month`}
            />
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select
            value={filters.status}
            onChange={(e) => setFilters({ status: e.target.value })}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>

          <select
            value={filters.minScore}
            onChange={(e) => setFilters({ minScore: e.target.value })}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="">All scores</option>
            <option value="70">High (70+)</option>
            <option value="40">Medium (40+)</option>
            <option value="1">Any score</option>
          </select>
        </div>

        {/* Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500 text-sm">Loading leads…</div>
          ) : leads.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-slate-400 text-sm">No leads yet.</p>
              <p className="text-slate-600 text-xs mt-1">Hover over a business on the map and click "Add to Leads".</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-left">
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Business</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Score</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Priority</th>
                  <th className="px-4 py-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Added</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {leads.map((lead) => {
                  const score = lead.business?.overall_score
                  const scoreColor = getScoreColor(score)
                  const category = lead.business?.place_types?.[0]?.replace(/_/g, ' ') ?? ''
                  const addedDate = new Date(lead.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

                  return (
                    <tr key={lead.id} className="hover:bg-slate-800/50 transition-colors group">
                      <td className="px-4 py-3">
                        <Link to={`/leads/${lead.id}`} className="block">
                          <div className="font-medium text-slate-100 leading-snug group-hover:text-blue-400 transition-colors">
                            {lead.business?.name}
                          </div>
                          <div className="text-xs text-slate-500 mt-0.5 capitalize">{category}</div>
                          {lead.business?.phone_number && (
                            <div className="text-xs text-slate-600 mt-0.5">{lead.business.phone_number}</div>
                          )}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        {score != null ? (
                          <div className="flex flex-col gap-0.5">
                            <span className="text-lg font-bold leading-none" style={{ color: scoreColor }}>{score}</span>
                            <span className="text-[10px] font-medium" style={{ color: scoreColor }}>{getScoreLabel(score)}</span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-600">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={lead.outreach_status}
                          onChange={(e) => handleStatusChange(lead.id, e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          className={`text-xs font-medium px-2 py-1 rounded-full border-0 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer ${STATUS_COLORS[lead.outreach_status] ?? 'bg-slate-700 text-slate-300'}`}
                        >
                          {STATUS_OPTIONS.slice(1).map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value={lead.priority}
                          onChange={(e) => updateLead(lead.id, { priority: e.target.value })}
                          onClick={(e) => e.stopPropagation()}
                          className={`text-xs font-medium bg-transparent border-0 focus:outline-none cursor-pointer capitalize ${PRIORITY_COLORS[lead.priority]}`}
                        >
                          {['low', 'medium', 'high', 'urgent'].map((p) => (
                            <option key={p} value={p}>{p}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{addedDate}</td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/leads/${lead.id}`}
                          className="text-xs text-slate-500 hover:text-blue-400 transition-colors px-2"
                        >
                          View →
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
