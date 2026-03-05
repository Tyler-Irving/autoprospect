import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useLeadStore } from '../store/leadStore'
import { getScoreColor, getScoreLabel } from '../utils/constants'

const STATUS_OPTIONS = [
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

function ScoreBar({ label, score }) {
  if (score == null) return null
  const color = getScoreColor(score)
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-slate-400 w-24 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs font-mono text-slate-300 w-6 text-right">{score}</span>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">{title}</h2>
      {children}
    </div>
  )
}

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { selectedLead: lead, fetchLead, updateLead, deleteLead, generateOutreach, clearSelected } = useLeadStore()
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [outreachTab, setOutreachTab] = useState('email')

  useEffect(() => {
    fetchLead(id)
    return () => clearSelected()
  }, [id])

  useEffect(() => {
    if (lead) setNotes(lead.notes ?? '')
  }, [lead?.id])

  if (!lead) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950 text-slate-500 text-sm">
        Loading…
      </div>
    )
  }

  const b = lead.business
  const score = b?.tier1_score
  const overall = b?.overall_score
  const scoreColor = getScoreColor(overall)
  const scoreLabel = getScoreLabel(overall)
  const e = b?.enrichment

  const handleSaveNotes = async () => {
    setSavingNotes(true)
    try {
      await updateLead(lead.id, { notes })
      toast.success('Notes saved')
    } catch {
      toast.error('Failed to save notes')
    } finally {
      setSavingNotes(false)
    }
  }

  const handleGenerateOutreach = () => {
    if (generating) return
    setGenerating(true)
    const businessName = b?.name
    const promise = generateOutreach(lead.id)
    promise.finally(() => setGenerating(false))
    toast.promise(promise, {
      loading: `Generating outreach for ${businessName}…`,
      success: `Outreach ready for ${businessName}`,
      error: (err) => err?.response?.data?.detail || `Failed to generate outreach for ${businessName}`,
    })
  }

  const handleCopy = (text, label) => {
    navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied`))
  }

  const handleDelete = async () => {
    if (!window.confirm(`Remove ${b?.name} from leads?`)) return
    await deleteLead(lead.id)
    toast.success('Lead removed')
    navigate('/leads')
  }

  const techFlags = e ? [
    e.has_online_booking && 'Online Booking',
    e.has_live_chat && 'Live Chat',
    e.has_contact_form && 'Contact Form',
    e.has_email_signup && 'Email Signup',
    e.has_ssl && 'SSL',
    e.is_mobile_responsive && 'Mobile Ready',
  ].filter(Boolean) : []

  const detectedTools = e ? [
    e.detected_crm && `CRM: ${e.detected_crm}`,
    e.detected_scheduling_tool && `Scheduling: ${e.detected_scheduling_tool}`,
    e.detected_email_platform && `Email: ${e.detected_email_platform}`,
    e.detected_payment_processor && `Payments: ${e.detected_payment_processor}`,
    e.website_platform && `Platform: ${e.website_platform}`,
  ].filter(Boolean) : []

  return (
    <div className="h-full overflow-auto bg-slate-950 p-6">
      <div className="max-w-4xl mx-auto space-y-5">

        {/* Breadcrumb + actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Link to="/leads" className="hover:text-slate-300 transition-colors">Leads</Link>
            <span>/</span>
            <span className="text-slate-300">{b?.name}</span>
          </div>
          <button
            onClick={handleDelete}
            className="text-xs text-slate-600 hover:text-red-400 transition-colors"
          >
            Remove lead
          </button>
        </div>

        {/* Header card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-white leading-tight">{b?.name}</h1>
              {b?.place_types?.[0] && (
                <p className="text-xs text-slate-500 mt-0.5 capitalize">{b.place_types[0].replace(/_/g, ' ')}</p>
              )}
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs text-slate-400">
                {b?.formatted_address && <span>📍 {b.formatted_address}</span>}
                {b?.phone_number && <span>📞 {b.phone_number}</span>}
                {b?.website_url && (
                  <a href={b.website_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">
                    🌐 Website
                  </a>
                )}
                {b?.rating && (
                  <span>⭐ {b.rating} ({b.total_reviews} reviews)</span>
                )}
              </div>
            </div>

            {/* Score badge */}
            {overall != null && (
              <div className="flex flex-col items-center shrink-0 bg-slate-800 rounded-xl px-5 py-3">
                <span className="text-3xl font-bold leading-none" style={{ color: scoreColor }}>{overall}</span>
                <span className="text-xs font-semibold uppercase tracking-wide mt-1" style={{ color: scoreColor }}>{scoreLabel}</span>
                <span className="text-[10px] text-slate-600 mt-0.5">AI Score</span>
              </div>
            )}
          </div>

          {/* Status + priority row */}
          <div className="flex items-center gap-3 mt-4 pt-4 border-t border-slate-800">
            <select
              value={lead.outreach_status}
              onChange={(e) => updateLead(lead.id, { outreach_status: e.target.value })}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>

            <select
              value={lead.priority}
              onChange={(e) => updateLead(lead.id, { priority: e.target.value })}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
            >
              {['low', 'medium', 'high', 'urgent'].map((p) => (
                <option key={p} value={p} className="capitalize">{p.charAt(0).toUpperCase() + p.slice(1)} priority</option>
              ))}
            </select>
          </div>
        </div>

        {/* Two column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

          {/* AI Score breakdown */}
          {score && (
            <Section title="Automation Readiness">
              <div className="space-y-2.5">
                <ScoreBar label="CRM" score={score.crm_score} />
                <ScoreBar label="Scheduling" score={score.scheduling_score} />
                <ScoreBar label="Marketing" score={score.marketing_score} />
                <ScoreBar label="Invoicing" score={score.invoicing_score} />
              </div>
              {score.key_signals?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {score.key_signals.map((sig, i) => (
                    <span key={i} className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60">
                      {sig}
                    </span>
                  ))}
                </div>
              )}
              {score.summary && (
                <p className="text-xs text-slate-400 leading-relaxed italic border-t border-slate-800 pt-3">
                  &ldquo;{score.summary}&rdquo;
                </p>
              )}
              {score.recommended_pitch_angle && (
                <div className="bg-blue-950/40 border border-blue-900/40 rounded-lg px-3 py-2">
                  <p className="text-[10px] text-blue-400 uppercase tracking-wide font-semibold mb-1">Pitch angle</p>
                  <p className="text-xs text-slate-300">{score.recommended_pitch_angle}</p>
                </div>
              )}
            </Section>
          )}

          {/* Tech stack */}
          <Section title="Website & Tech Stack">
            {e ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {e.website_reachable === false && (
                    <span className="text-xs px-2 py-0.5 rounded bg-red-900/40 text-red-400 border border-red-900/40">No website</span>
                  )}
                  {techFlags.map((f) => (
                    <span key={f} className="text-xs px-2 py-0.5 rounded bg-green-900/30 text-green-400 border border-green-900/30">{f}</span>
                  ))}
                </div>
                {detectedTools.length > 0 && (
                  <div className="space-y-1">
                    {detectedTools.map((t) => (
                      <div key={t} className="text-xs text-slate-400 flex items-center gap-1.5">
                        <span className="text-slate-600">▸</span>{t}
                      </div>
                    ))}
                  </div>
                )}
                {(e.detected_analytics || []).length > 0 && (
                  <div className="text-xs text-slate-500">Analytics: {e.detected_analytics.join(', ')}</div>
                )}
                <div className="flex flex-wrap gap-3 text-xs text-slate-500 pt-1">
                  {e.facebook_url && <a href={e.facebook_url} target="_blank" rel="noreferrer" className="hover:text-blue-400">Facebook</a>}
                  {e.instagram_url && <a href={e.instagram_url} target="_blank" rel="noreferrer" className="hover:text-pink-400">Instagram</a>}
                  {e.linkedin_url && <a href={e.linkedin_url} target="_blank" rel="noreferrer" className="hover:text-blue-300">LinkedIn</a>}
                  {e.yelp_url && <a href={e.yelp_url} target="_blank" rel="noreferrer" className="hover:text-red-400">Yelp</a>}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-600">No enrichment data.</p>
            )}
          </Section>
        </div>

        {/* Notes */}
        <Section title="Notes">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={handleSaveNotes}
            rows={4}
            placeholder="Add notes about this prospect…"
            className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2.5 placeholder-slate-600 focus:outline-none focus:border-blue-500 resize-none"
          />
          <div className="flex justify-end">
            <button
              onClick={handleSaveNotes}
              disabled={savingNotes}
              className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              {savingNotes ? 'Saving…' : 'Save notes'}
            </button>
          </div>
        </Section>

        {/* AI Outreach */}
        <Section title="AI Outreach">
          {lead.outreach_generated_at ? (
            <div className="space-y-3">
              {/* Tab switcher */}
              <div className="flex gap-1 bg-slate-800 p-1 rounded-lg w-fit">
                <button
                  onClick={() => setOutreachTab('email')}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    outreachTab === 'email'
                      ? 'bg-slate-700 text-slate-100'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  Email
                </button>
                <button
                  onClick={() => setOutreachTab('call')}
                  className={`text-xs px-3 py-1.5 rounded-md font-medium transition-colors ${
                    outreachTab === 'call'
                      ? 'bg-slate-700 text-slate-100'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  Call Script
                </button>
              </div>

              {outreachTab === 'email' && (
                <div className="space-y-2">
                  {lead.generated_email_subject && (
                    <div className="bg-slate-800 rounded-lg px-3 py-2">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold mb-1">Subject</p>
                      <p className="text-sm text-slate-200">{lead.generated_email_subject}</p>
                    </div>
                  )}
                  {lead.generated_email && (
                    <div className="relative bg-slate-800 rounded-lg px-3 py-3">
                      <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold mb-2">Body</p>
                      <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">{lead.generated_email}</p>
                      <button
                        onClick={() => handleCopy(`Subject: ${lead.generated_email_subject}\n\n${lead.generated_email}`, 'Email')}
                        className="absolute top-2 right-2 text-[10px] text-slate-500 hover:text-slate-300 bg-slate-700 px-2 py-1 rounded transition-colors"
                      >
                        Copy
                      </button>
                    </div>
                  )}
                </div>
              )}

              {outreachTab === 'call' && (
                <div className="relative bg-slate-800 rounded-lg px-3 py-3">
                  <p className="text-[10px] text-slate-500 uppercase tracking-wide font-semibold mb-2">Script</p>
                  <p className="text-sm text-slate-300 whitespace-pre-line leading-relaxed font-mono">
                    {lead.generated_call_script}
                  </p>
                  <button
                    onClick={() => handleCopy(lead.generated_call_script, 'Call script')}
                    className="absolute top-2 right-2 text-[10px] text-slate-500 hover:text-slate-300 bg-slate-700 px-2 py-1 rounded transition-colors"
                  >
                    Copy
                  </button>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <span className="text-[10px] text-slate-600">
                  Generated {new Date(lead.outreach_generated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                <button
                  onClick={handleGenerateOutreach}
                  disabled={generating}
                  className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors disabled:opacity-50"
                >
                  Regenerate
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center py-4 gap-3">
              {generating ? (
                <>
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm text-slate-500">Writing outreach…</p>
                </>
              ) : (
                <>
                  <p className="text-sm text-slate-500 text-center">
                    Generate a personalized cold email and call script based on this business's automation score and signals.
                  </p>
                  <button
                    onClick={handleGenerateOutreach}
                    className="text-sm bg-blue-600 hover:bg-blue-500 text-white font-semibold px-5 py-2 rounded-lg transition-colors"
                  >
                    Generate Email + Call Script
                  </button>
                </>
              )}
            </div>
          )}
        </Section>

        {/* Activity log */}
        {lead.activities?.length > 0 && (
          <Section title="Activity Log">
            <div className="space-y-2">
              {lead.activities.map((a) => (
                <div key={a.id} className="flex items-start gap-3 text-xs">
                  <span className="text-slate-600 shrink-0 mt-0.5">
                    {new Date(a.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                  <span className="text-slate-400">{a.description}</span>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  )
}
