import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useToasts } from '@/components/ui/toast'
import { useLeadStore } from '../store/leadStore'
import { getScoreColor, getScoreLabel } from '../utils/constants'
import { businessesApi } from '../api/businesses'

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
      <span className="text-xs w-24 shrink-0" style={{ color: 'var(--muted-foreground)' }}>{label}</span>
      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--secondary)' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-xs font-mono w-6 text-right" style={{ color: 'var(--foreground)' }}>{score}</span>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="rounded-xl p-5 space-y-4" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
      <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--muted-foreground)' }}>{title}</h2>
      {children}
    </div>
  )
}

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { selectedLead: lead, fetchLead, updateLead, deleteLead, generateOutreach, sendEmail, clearSelected } = useLeadStore()
  const toasts = useToasts()
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [sending, setSending] = useState(false)
  const [showDossier, setShowDossier] = useState(false)
  const tier2PollRef = useRef(null)
  const [outreachTab, setOutreachTab] = useState('email')
  const [contactEmail, setContactEmail] = useState('')
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setShowDossier(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    fetchLead(id).catch(() => toasts.error('Failed to load lead'))
    return () => clearSelected()
  }, [id])

  useEffect(() => {
    if (lead) {
      setNotes(lead.notes ?? '')
      setContactEmail(lead.contact_email ?? '')
    }
  }, [lead?.id])

  // Poll while the DB says tier2_pending — survives navigation and page refresh
  useEffect(() => {
    if (!lead?.business?.tier2_pending) return

    tier2PollRef.current = setInterval(async () => {
      try {
        const updated = await fetchLead(id)
        if (!updated?.business?.tier2_pending) {
          clearInterval(tier2PollRef.current)
          if (updated?.business?.tier2_score) {
            toasts.success('Deep analysis complete')
          }
        }
      } catch {
        // silently continue polling
      }
    }, 5000)

    return () => clearInterval(tier2PollRef.current)
  }, [lead?.id, lead?.business?.tier2_pending])

  if (!lead) {
    return (
      <div className="h-full flex items-center justify-center text-sm" style={{ background: 'var(--background)', color: 'var(--muted-foreground)' }}>
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
      toasts.success('Notes saved')
    } catch {
      toasts.error('Failed to save notes')
    } finally {
      setSavingNotes(false)
    }
  }

  const handleGenerateOutreach = () => {
    if (generating) return
    setGenerating(true)
    const businessName = b?.name
    const promise = generateOutreach(lead.id)
    promise.finally(() => { if (mountedRef.current) setGenerating(false) })
    toasts.promise(promise, {
      loading: `Generating outreach for ${businessName}…`,
      success: `Outreach ready for ${businessName}`,
      error: (err) => err?.response?.data?.detail || `Failed to generate outreach for ${businessName}`,
    })
  }

  const handleCopy = (text, label) => {
    navigator.clipboard.writeText(text)
      .then(() => toasts.success(`${label} copied`))
      .catch(() => toasts.error('Copy failed — check browser permissions'))
  }

  const handleContactEmailBlur = async () => {
    if (contactEmail === (lead.contact_email ?? '')) return
    await updateLead(lead.id, { contact_email: contactEmail })
  }

  const handleSendEmail = () => {
    if (sending) return
    setSending(true)
    const businessName = b?.name
    const promise = sendEmail(lead.id)
    promise.finally(() => { if (mountedRef.current) setSending(false) })
    toasts.promise(promise, {
      loading: `Sending email to ${businessName}…`,
      success: `Email sent to ${businessName}`,
      error: (err) => err?.response?.data?.detail || `Failed to send email to ${businessName}`,
    })
  }

  const handleRunTier2 = async () => {
    try {
      await businessesApi.enrichTier2(b.id)
      await fetchLead(id)
      toasts.success('Deep analysis complete')
    } catch {
      toasts.error('Deep analysis failed')
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(`Remove ${b?.name} from leads?`)) return
    try {
      await deleteLead(lead.id)
      toasts.success('Lead removed')
      navigate('/leads')
    } catch {
      toasts.error('Failed to remove lead')
    }
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
    <div className="h-full overflow-auto p-6" style={{ background: 'var(--background)' }}>
      <div className="max-w-4xl mx-auto space-y-5">

        {/* Breadcrumb + actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--muted-foreground)' }}>
            <Link to="/leads" className="hover:text-[#f97316] transition-colors">Leads</Link>
            <span>/</span>
            <span style={{ color: 'var(--foreground)' }}>{b?.name}</span>
          </div>
          <button
            onClick={handleDelete}
            className="text-xs hover:text-red-400 transition-colors"
            style={{ color: 'var(--muted-foreground)' }}
          >
            Remove lead
          </button>
        </div>

        {/* Header card */}
        <div className="rounded-xl p-5" style={{ background: 'var(--card)', border: '1px solid var(--border)' }}>
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold leading-tight" style={{ color: 'var(--foreground)' }}>{b?.name}</h1>
              {b?.place_types?.[0] && (
                <p className="text-xs mt-0.5 capitalize" style={{ color: 'var(--muted-foreground)' }}>{b.place_types[0].replace(/_/g, ' ')}</p>
              )}
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs" style={{ color: 'var(--muted-foreground)' }}>
                {b?.formatted_address && <span>📍 {b.formatted_address}</span>}
                {b?.phone_number && <span>📞 {b.phone_number}</span>}
                {b?.website_url && (
                  <a href={b.website_url} target="_blank" rel="noreferrer" className="hover:underline" style={{ color: '#f97316' }}>
                    🌐 Website
                  </a>
                )}
                {b?.rating && (
                  <span>⭐ {b.rating} ({b.total_reviews} reviews)</span>
                )}
                {lead.contact_email && (
                  <span className="flex items-center gap-1.5">
                    <a href={`mailto:${lead.contact_email}`} className="hover:underline" style={{ color: 'var(--foreground)' }}>
                      ✉ {lead.contact_email}
                    </a>
                    {e?.contact_email && e.contact_email === lead.contact_email && (
                      <span className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'color-mix(in srgb, #22c55e 15%, transparent)', color: '#22c55e', border: '1px solid color-mix(in srgb, #22c55e 30%, transparent)' }}>
                        auto-found
                      </span>
                    )}
                  </span>
                )}
              </div>
            </div>

            {/* Score badge */}
            {overall != null && (
              <div className="flex flex-col items-center shrink-0 rounded-xl px-5 py-3" style={{ background: 'var(--secondary)' }}>
                <span className="text-3xl font-bold leading-none" style={{ color: scoreColor }}>{overall}</span>
                <span className="text-xs font-semibold uppercase tracking-wide mt-1" style={{ color: scoreColor }}>{scoreLabel}</span>
                <span className="text-[10px] mt-0.5" style={{ color: 'var(--muted-foreground)' }}>AI Score</span>
              </div>
            )}
          </div>

          {/* Status + priority row */}
          <div className="flex items-center gap-3 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
            <select
              value={lead.outreach_status}
              onChange={(e) => updateLead(lead.id, { outreach_status: e.target.value })}
              className="text-sm px-3 py-1.5 rounded-lg focus:outline-none"
              style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>

            <select
              value={lead.priority}
              onChange={(e) => updateLead(lead.id, { priority: e.target.value })}
              className="text-sm px-3 py-1.5 rounded-lg focus:outline-none"
              style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
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
                    <span key={i} className="text-xs px-2.5 py-0.5 rounded-full" style={{ background: 'var(--secondary)', color: 'var(--foreground)', border: '1px solid var(--border)' }}>
                      {sig}
                    </span>
                  ))}
                </div>
              )}
              {score.summary && (
                <p className="text-xs leading-relaxed italic pt-3" style={{ color: 'var(--muted-foreground)', borderTop: '1px solid var(--border)' }}>
                  &ldquo;{score.summary}&rdquo;
                </p>
              )}
              {score.recommended_pitch_angle && (
                <div className="rounded-lg px-3 py-2" style={{ background: 'color-mix(in srgb, #f97316 10%, transparent)', border: '1px solid color-mix(in srgb, #f97316 25%, transparent)' }}>
                  <p className="text-[10px] uppercase tracking-wide font-semibold mb-1" style={{ color: '#f97316' }}>Pitch angle</p>
                  <p className="text-xs" style={{ color: 'var(--foreground)' }}>{score.recommended_pitch_angle}</p>
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
                    <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'color-mix(in srgb, #ef4444 15%, transparent)', color: '#ef4444', border: '1px solid color-mix(in srgb, #ef4444 30%, transparent)' }}>No website</span>
                  )}
                  {techFlags.map((f) => (
                    <span key={f} className="text-xs px-2 py-0.5 rounded" style={{ background: 'color-mix(in srgb, #22c55e 15%, transparent)', color: '#22c55e', border: '1px solid color-mix(in srgb, #22c55e 30%, transparent)' }}>{f}</span>
                  ))}
                </div>
                {detectedTools.length > 0 && (
                  <div className="space-y-1">
                    {detectedTools.map((t) => (
                      <div key={t} className="text-xs flex items-center gap-1.5" style={{ color: 'var(--muted-foreground)' }}>
                        <span style={{ opacity: 0.5 }}>▸</span>{t}
                      </div>
                    ))}
                  </div>
                )}
                {(e.detected_analytics || []).length > 0 && (
                  <div className="text-xs" style={{ color: 'var(--muted-foreground)' }}>Analytics: {e.detected_analytics.join(', ')}</div>
                )}
                <div className="flex flex-wrap gap-3 text-xs pt-1" style={{ color: 'var(--muted-foreground)' }}>
                  {e.facebook_url && <a href={e.facebook_url} target="_blank" rel="noreferrer" className="hover:text-[#f97316] transition-colors">Facebook</a>}
                  {e.instagram_url && <a href={e.instagram_url} target="_blank" rel="noreferrer" className="hover:text-[#f97316] transition-colors">Instagram</a>}
                  {e.linkedin_url && <a href={e.linkedin_url} target="_blank" rel="noreferrer" className="hover:text-[#f97316] transition-colors">LinkedIn</a>}
                  {e.yelp_url && <a href={e.yelp_url} target="_blank" rel="noreferrer" className="hover:text-[#f97316] transition-colors">Yelp</a>}
                </div>
              </div>
            ) : (
              <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>No enrichment data.</p>
            )}
          </Section>
        </div>

        {/* Dossier modal */}
        {showDossier && b?.tier2_score && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-6"
            style={{ background: 'rgba(0,0,0,0.7)' }}
            onClick={() => setShowDossier(false)}
          >
            <div
              className="relative w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
              style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal header */}
              <div className="flex items-center justify-between px-8 py-5 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
                <div>
                  <h2 className="text-base font-semibold" style={{ color: 'var(--foreground)' }}>Full Deep Analysis</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--muted-foreground)' }}>{b.name}</p>
                </div>
                <button
                  onClick={() => setShowDossier(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors"
                  style={{ color: 'var(--muted-foreground)' }}
                >
                  ✕
                </button>
              </div>

              {/* Modal body — scrollable */}
              <div className="overflow-y-auto px-8 py-6 space-y-8">
                <div className="space-y-3">
                  <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--muted-foreground)' }}>Full Dossier</p>
                  <p className="text-base leading-8 whitespace-pre-line" style={{ color: 'var(--foreground)' }}>{b.tier2_score.full_dossier}</p>
                </div>
                <div className="space-y-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '2rem' }}>
                  <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--muted-foreground)' }}>Competitor Analysis</p>
                  <p className="text-base leading-8 whitespace-pre-line" style={{ color: 'var(--foreground)' }}>{b.tier2_score.competitor_analysis}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Deep Analysis */}
        <Section title="Deep Analysis">
          {b?.tier2_score ? (
            <div className="space-y-4">
              {/* Summary */}
              {b.tier2_score.summary && (
                <p className="text-sm leading-relaxed" style={{ color: 'var(--foreground)' }}>{b.tier2_score.summary}</p>
              )}

              {/* Key signals */}
              {b.tier2_score.key_signals?.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {b.tier2_score.key_signals.map((sig, i) => (
                    <span key={i} className="text-xs px-2.5 py-0.5 rounded-full" style={{ background: 'var(--secondary)', color: 'var(--foreground)', border: '1px solid var(--border)' }}>
                      {sig}
                    </span>
                  ))}
                </div>
              )}

              {/* Pitch angle */}
              {b.tier2_score.recommended_pitch_angle && (
                <div className="rounded-lg px-3 py-2" style={{ background: 'color-mix(in srgb, #f97316 10%, transparent)', border: '1px solid color-mix(in srgb, #f97316 25%, transparent)' }}>
                  <p className="text-[10px] uppercase tracking-wide font-semibold mb-1" style={{ color: '#f97316' }}>Pitch angle</p>
                  <p className="text-xs" style={{ color: 'var(--foreground)' }}>{b.tier2_score.recommended_pitch_angle}</p>
                </div>
              )}

              {/* View full dossier CTA */}
              <button
                onClick={() => setShowDossier(true)}
                className="w-full py-2 rounded-lg text-sm font-medium transition-colors hover:opacity-90"
                style={{ background: 'var(--secondary)', color: 'var(--foreground)', border: '1px solid var(--border)' }}
              >
                View Full Analysis →
              </button>

              {b.tier2_pending && (
                <div className="flex items-center gap-2 py-2" style={{ borderTop: '1px solid var(--border)' }}>
                  <div className="w-3.5 h-3.5 shrink-0 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#f97316', borderTopColor: 'transparent' }} />
                  <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>Re-analyzing…</p>
                </div>
              )}
              <div className="flex items-center justify-between" style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
                <span className="text-[10px] font-mono" style={{ color: 'var(--muted-foreground)' }}>
                  Analyzed {new Date(b.tier2_score.scored_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono" style={{ color: 'var(--muted-foreground)' }}>
                    ${(b.tier2_score.api_cost_cents / 100).toFixed(2)}
                  </span>
                  <button
                    onClick={handleRunTier2}
                    disabled={b.tier2_pending}
                    className="text-[10px] hover:opacity-80 transition-opacity disabled:opacity-50"
                    style={{ color: 'var(--muted-foreground)' }}
                  >
                    {b.tier2_pending ? 'Running…' : 'Re-run'}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center py-4 gap-3">
              {b.tier2_pending ? (
                <div className="w-full py-2 flex flex-col items-center gap-3">
                  <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#f97316', borderTopColor: 'transparent' }} />
                  <p className="text-sm" style={{ color: 'var(--foreground)' }}>Deep analysis running…</p>
                  <p className="text-xs" style={{ color: 'var(--muted-foreground)' }}>Claude is writing a full dossier. This takes 20–60 seconds.</p>
                </div>
              ) : (
                <>
                  <p className="text-sm text-center" style={{ color: 'var(--muted-foreground)' }}>
                    Run a deeper Claude analysis for a full dossier, tool recommendations, ROI argument, and competitor comparison. ~$0.10.
                  </p>
                  <button
                    onClick={handleRunTier2}
                    className="text-sm font-semibold px-5 py-2 rounded-lg transition-colors hover:opacity-90"
                    style={{ background: '#f97316', color: '#fff' }}
                  >
                    Run Deep Analysis
                  </button>
                </>
              )}
            </div>
          )}
        </Section>

        {/* Notes */}
        <Section title="Notes">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={handleSaveNotes}
            rows={4}
            placeholder="Add notes about this prospect…"
            className="w-full text-sm rounded-lg px-3 py-2.5 focus:outline-none resize-none"
            style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
          />
          <div className="flex justify-end">
            <button
              onClick={handleSaveNotes}
              disabled={savingNotes}
              className="text-xs px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
              style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
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
              <div className="flex gap-1 p-1 rounded-lg w-fit" style={{ background: 'var(--secondary)' }}>
                <button
                  onClick={() => setOutreachTab('email')}
                  className="text-xs px-3 py-1.5 rounded-md font-medium transition-colors"
                  style={outreachTab === 'email'
                    ? { background: 'var(--card)', color: 'var(--foreground)' }
                    : { color: 'var(--muted-foreground)' }}
                >
                  Email
                </button>
                <button
                  onClick={() => setOutreachTab('call')}
                  className="text-xs px-3 py-1.5 rounded-md font-medium transition-colors"
                  style={outreachTab === 'call'
                    ? { background: 'var(--card)', color: 'var(--foreground)' }
                    : { color: 'var(--muted-foreground)' }}
                >
                  Call Script
                </button>
              </div>

              {outreachTab === 'email' && (
                <div className="space-y-2">
                  {lead.generated_email_subject && (
                    <div className="rounded-lg px-3 py-2" style={{ background: 'var(--secondary)' }}>
                      <p className="text-[10px] uppercase tracking-wide font-semibold mb-1" style={{ color: 'var(--muted-foreground)' }}>Subject</p>
                      <p className="text-sm" style={{ color: 'var(--foreground)' }}>{lead.generated_email_subject}</p>
                    </div>
                  )}
                  {lead.generated_email && (
                    <div className="relative rounded-lg px-3 py-3" style={{ background: 'var(--secondary)' }}>
                      <p className="text-[10px] uppercase tracking-wide font-semibold mb-2" style={{ color: 'var(--muted-foreground)' }}>Body</p>
                      <p className="text-sm whitespace-pre-line leading-relaxed" style={{ color: 'var(--foreground)' }}>{lead.generated_email}</p>
                      <button
                        onClick={() => handleCopy(`Subject: ${lead.generated_email_subject}\n\n${lead.generated_email}`, 'Email')}
                        className="absolute top-2 right-2 text-[10px] px-2 py-1 rounded transition-colors hover:opacity-80"
                        style={{ color: 'var(--muted-foreground)', background: 'var(--card)' }}
                      >
                        Copy
                      </button>
                    </div>
                  )}

                  {/* Send section */}
                  <div className="pt-1 space-y-2">
                    <div>
                      <label className="text-[10px] uppercase tracking-wide font-semibold block mb-1" style={{ color: 'var(--muted-foreground)' }}>
                        Recipient Email
                      </label>
                      <input
                        type="email"
                        value={contactEmail}
                        onChange={(e) => setContactEmail(e.target.value)}
                        onBlur={handleContactEmailBlur}
                        placeholder="owner@business.com"
                        className="w-full text-sm rounded-lg px-3 py-2 focus:outline-none"
                        style={{ background: 'var(--secondary)', border: '1px solid var(--border)', color: 'var(--foreground)' }}
                      />
                    </div>
                    <button
                      onClick={handleSendEmail}
                      disabled={sending || !contactEmail.trim()}
                      className="w-full py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      style={{ background: '#f97316', color: '#fff' }}
                    >
                      {sending ? 'Sending…' : lead.contact_attempts > 0 ? `Send Again (sent ${lead.contact_attempts}×)` : 'Send Email'}
                    </button>
                  </div>
                </div>
              )}

              {outreachTab === 'call' && (
                <div className="relative rounded-lg px-3 py-3" style={{ background: 'var(--secondary)' }}>
                  <p className="text-[10px] uppercase tracking-wide font-semibold mb-2" style={{ color: 'var(--muted-foreground)' }}>Script</p>
                  <p className="text-sm whitespace-pre-line leading-relaxed font-mono" style={{ color: 'var(--foreground)' }}>
                    {lead.generated_call_script}
                  </p>
                  <button
                    onClick={() => handleCopy(lead.generated_call_script, 'Call script')}
                    className="absolute top-2 right-2 text-[10px] px-2 py-1 rounded transition-colors hover:opacity-80"
                    style={{ color: 'var(--muted-foreground)', background: 'var(--card)' }}
                  >
                    Copy
                  </button>
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <span className="text-[10px]" style={{ color: 'var(--muted-foreground)' }}>
                  Generated {new Date(lead.outreach_generated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                </span>
                <button
                  onClick={handleGenerateOutreach}
                  disabled={generating}
                  className="text-[10px] hover:opacity-80 transition-opacity disabled:opacity-50"
                  style={{ color: 'var(--muted-foreground)' }}
                >
                  Regenerate
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center py-4 gap-3">
              {generating ? (
                <>
                  <div className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: '#f97316', borderTopColor: 'transparent' }} />
                  <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>Writing outreach…</p>
                </>
              ) : (
                <>
                  <p className="text-sm text-center" style={{ color: 'var(--muted-foreground)' }}>
                    Generate a personalized cold email and call script based on this business's automation score and signals.
                  </p>
                  <button
                    onClick={handleGenerateOutreach}
                    className="text-sm font-semibold px-5 py-2 rounded-lg transition-colors hover:opacity-90"
                    style={{ background: '#f97316', color: '#fff' }}
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
                  <span className="shrink-0 mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
                    {new Date(a.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                  <span style={{ color: 'var(--muted-foreground)' }}>{a.description}</span>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>
    </div>
  )
}
