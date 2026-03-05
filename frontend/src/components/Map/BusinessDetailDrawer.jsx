import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useMapStore } from '../../store/mapStore'
import { useLeadStore } from '../../store/leadStore'
import { getScoreColor, getScoreLabel } from '../../utils/constants'

const DEAL_COLORS = {
  low: 'text-slate-400',
  medium: 'text-yellow-400',
  high: 'text-green-400',
  enterprise: 'text-blue-400',
}

function ScoreBar({ label, score }) {
  if (score == null) return null
  const color = getScoreColor(score)
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-400">{label}</span>
        <span className="text-xs font-mono font-medium" style={{ color }}>{score}</span>
      </div>
      <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  )
}

function SectionLabel({ children }) {
  return (
    <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-3">
      {children}
    </div>
  )
}

export default function BusinessDetailDrawer({ onPromote, promoting, promoted }) {
  const { selectedBusiness: b, setSelectedBusiness } = useMapStore()
  const isOpen = !!b

  // Escape key to close
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setSelectedBusiness(null) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [setSelectedBusiness])

  const t = b?.tier1_score
  const score = b?.overall_score
  const scoreColor = getScoreColor(score)
  const scoreLabel = getScoreLabel(score)
  const isPromoted = promoted[b?.id] || b?.has_lead
  const isPromoting = promoting[b?.id]

  const websiteDisplay = b?.website_url
    ? b.website_url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')
    : null

  return (
    <>
      {/* Drawer */}
      <div
        className="fixed top-0 right-0 bottom-0 w-[380px] z-40 flex flex-col"
        style={{
          background: '#0f172a',
          borderLeft: '1px solid #334155',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: isOpen
            ? 'transform 180ms cubic-bezier(0.0, 0.0, 0.2, 1)'
            : 'transform 150ms cubic-bezier(0.4, 0.0, 1, 1)',
        }}
      >
        {b && (
          <>
            {/* Fixed header */}
            <div className="flex items-start justify-between px-5 py-4 border-b border-slate-700 shrink-0">
              <div className="flex-1 min-w-0 pr-3">
                <h2 className="text-base font-semibold text-slate-100 leading-snug truncate">
                  {b.name}
                </h2>
                {b.category && (
                  <p className="text-xs text-slate-500 mt-0.5 capitalize">
                    {b.category.replace(/_/g, ' ')}
                  </p>
                )}
              </div>
              <button
                onClick={() => setSelectedBusiness(null)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-100 hover:bg-slate-800 transition-colors shrink-0"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto">

              {/* Group A — Qualification */}
              <div className="px-5 py-4 border-b border-slate-800">
                <div className="flex items-center gap-4">
                  <div
                    className="w-16 h-16 rounded-xl flex flex-col items-center justify-center shrink-0"
                    style={{
                      background: score != null ? `${scoreColor}18` : '#1e293b',
                      border: `1px solid ${score != null ? scoreColor + '40' : '#334155'}`,
                    }}
                  >
                    <span
                      className="text-2xl font-bold leading-none"
                      style={{ color: score != null ? scoreColor : '#475569' }}
                    >
                      {score ?? '—'}
                    </span>
                    {score != null && (
                      <span
                        className="text-[9px] font-semibold uppercase tracking-wide mt-0.5"
                        style={{ color: scoreColor }}
                      >
                        {scoreLabel}
                      </span>
                    )}
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 mb-0.5">Automation Score</p>
                    {t?.estimated_deal_value && (
                      <p className={`text-sm font-semibold capitalize ${DEAL_COLORS[t.estimated_deal_value]}`}>
                        {t.estimated_deal_value} deal potential
                      </p>
                    )}
                    {t?.confidence != null && (
                      <p className="text-xs text-slate-600 mt-0.5">
                        {Math.round(t.confidence * 100)}% confidence
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Group B — Contact */}
              <div className="px-5 py-4 border-b border-slate-800 space-y-2">
                <SectionLabel>Contact</SectionLabel>
                {b.formatted_address && (
                  <div className="flex items-start gap-2 text-sm">
                    <span className="text-slate-600 shrink-0 mt-0.5 text-xs">▸</span>
                    <span className="text-slate-400 leading-snug">{b.formatted_address}</span>
                  </div>
                )}
                {b.phone_number && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-600 text-xs">▸</span>
                    <a href={`tel:${b.phone_number}`} className="text-slate-300 hover:text-white transition-colors">
                      {b.phone_number}
                    </a>
                  </div>
                )}
                {websiteDisplay && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-600 text-xs">▸</span>
                    <a
                      href={b.website_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-400 hover:text-blue-300 underline-offset-2 hover:underline truncate transition-colors"
                    >
                      {websiteDisplay}
                    </a>
                  </div>
                )}
                {b.rating != null && (
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-slate-600 text-xs">▸</span>
                    <span className="text-slate-400">
                      <span className="text-yellow-400">★</span>{' '}
                      <span className="text-slate-200 font-medium">{b.rating}</span>
                      {b.total_reviews > 0 && (
                        <span className="text-slate-600 ml-1">({b.total_reviews.toLocaleString()} reviews)</span>
                      )}
                    </span>
                  </div>
                )}
              </div>

              {/* Group C — Sub-score bars */}
              {t && (
                <div className="px-5 py-4 border-b border-slate-800 space-y-3">
                  <SectionLabel>Automation Readiness</SectionLabel>
                  <ScoreBar label="CRM Fit" score={t.crm_score} />
                  <ScoreBar label="Scheduling Fit" score={t.scheduling_score} />
                  <ScoreBar label="Marketing Fit" score={t.marketing_score} />
                  <ScoreBar label="Invoicing Fit" score={t.invoicing_score} />
                </div>
              )}

              {/* Group D — Key signals */}
              {t?.key_signals?.length > 0 && (
                <div className="px-5 py-4 border-b border-slate-800">
                  <SectionLabel>Detected Signals</SectionLabel>
                  <div className="flex flex-wrap gap-1.5">
                    {t.key_signals.map((sig, i) => (
                      <span
                        key={i}
                        className="text-xs px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700"
                      >
                        {sig}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Group E — AI summary + pitch */}
              {(t?.summary || t?.recommended_pitch_angle) && (
                <div className="px-5 py-4 border-b border-slate-800 space-y-3">
                  <SectionLabel>AI Assessment</SectionLabel>
                  {t.summary && (
                    <p className="text-sm text-slate-300 leading-relaxed">{t.summary}</p>
                  )}
                  {t.recommended_pitch_angle && (
                    <div className="border-l-2 border-blue-600 pl-3">
                      <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Pitch angle</p>
                      <p className="text-sm text-slate-200 leading-relaxed">{t.recommended_pitch_angle}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Bottom padding so content isn't hidden behind footer */}
              <div className="h-4" />
            </div>

            {/* Pinned footer — CTA always visible */}
            <div className="shrink-0 px-5 py-4 border-t border-slate-700 bg-slate-900">
              <div className="flex gap-2">
                <button
                  onClick={() => onPromote(b)}
                  disabled={isPromoting || isPromoted}
                  className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-colors ${
                    isPromoted
                      ? 'bg-slate-700 text-slate-400 cursor-default'
                      : 'bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50'
                  }`}
                >
                  {isPromoting ? 'Adding…' : isPromoted ? 'Already in Leads' : 'Add to Leads'}
                </button>
                {isPromoted && (
                  <Link
                    to="/leads"
                    className="flex items-center justify-center px-4 py-2.5 rounded-lg text-sm font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                  >
                    View
                  </Link>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
