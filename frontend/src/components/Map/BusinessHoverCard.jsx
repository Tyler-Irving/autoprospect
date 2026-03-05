import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { useMapStore } from '../../store/mapStore'
import { useLeadStore } from '../../store/leadStore'
import { getScoreColor, getScoreLabel } from '../../utils/constants'

function ScoreBar({ label, score }) {
  if (score === null || score === undefined) return null
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${score}%`, background: getScoreColor(score) }}
        />
      </div>
      <span className="text-xs font-mono text-slate-300 w-6 text-right">{score}</span>
    </div>
  )
}

export default function BusinessHoverCard() {
  const { hoveredBusiness: b, hoverPosition } = useMapStore()
  const { promoteBusiness } = useLeadStore()
  const [promoting, setPromoting] = useState(false)
  const [promoted, setPromoted] = useState(false)

  // Reset per-hover state whenever the hovered business changes so that
  // promoting business A and then hovering business B does not incorrectly
  // show "In Leads" for B.
  useEffect(() => {
    setPromoted(false)
    setPromoting(false)
  }, [b?.id])

  if (!b || !hoverPosition) return null

  const score = b.tier1_score
  const scoreColor = getScoreColor(b.overall_score)
  const scoreLabel = getScoreLabel(b.overall_score)

  const category = b.category
    ? b.category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : null

  const websiteDisplay = b.website_url
    ? b.website_url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')
    : null

  const dealColors = {
    low: 'text-slate-400',
    medium: 'text-yellow-400',
    high: 'text-green-400',
    enterprise: 'text-blue-400',
  }

  const handlePromote = async (e) => {
    e.stopPropagation()
    if (promoting || promoted || b.has_lead) return
    setPromoting(true)
    try {
      const result = await promoteBusiness(b.id)
      setPromoted(true)
      toast.success(result.already_lead ? `${b.name} is already a lead` : `${b.name} added to leads`)
    } catch {
      toast.error('Failed to promote lead')
    } finally {
      setPromoting(false)
    }
  }

  return (
    <div
      className="fixed z-[9999] w-80"
      style={{ left: hoverPosition.x, top: hoverPosition.y, pointerEvents: 'none' }}
    >
      <div className="bg-slate-900/95 backdrop-blur-sm border border-slate-700/80 rounded-xl shadow-2xl shadow-black/60 overflow-hidden">

        {/* Header */}
        <div className="px-4 pt-3 pb-2 flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {category && (
              <span className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 mb-1 uppercase tracking-wide font-medium">
                {category}
              </span>
            )}
            <h3 className="text-sm font-semibold text-white leading-snug">{b.name}</h3>
          </div>
          <div className="flex flex-col items-end shrink-0">
            {b.overall_score !== null && b.overall_score !== undefined ? (
              <>
                <span className="text-2xl font-bold leading-none" style={{ color: scoreColor }}>
                  {b.overall_score}
                </span>
                <span
                  className="text-[10px] font-semibold uppercase tracking-wide mt-0.5"
                  style={{ color: scoreColor }}
                >
                  {scoreLabel}
                </span>
              </>
            ) : (
              <span className="text-xs text-slate-500 pt-1">Unscored</span>
            )}
          </div>
        </div>

        {/* Details row */}
        <div className="px-4 pb-3 space-y-1.5">
          {b.formatted_address && (
            <div className="flex items-start gap-1.5 text-xs text-slate-400">
              <span className="shrink-0 mt-px">📍</span>
              <span className="leading-snug">{b.formatted_address}</span>
            </div>
          )}
          {(b.rating || b.phone_number) && (
            <div className="flex items-center gap-4 text-xs text-slate-400">
              {b.rating && (
                <span className="flex items-center gap-1">
                  <span className="text-yellow-400">★</span>
                  <span className="text-slate-300 font-medium">{b.rating}</span>
                  {b.total_reviews > 0 && (
                    <span className="text-slate-500">· {b.total_reviews.toLocaleString()}</span>
                  )}
                </span>
              )}
              {b.phone_number && (
                <span className="flex items-center gap-1">
                  <span>📞</span>
                  <span>{b.phone_number}</span>
                </span>
              )}
            </div>
          )}
          {websiteDisplay && (
            <div className="flex items-center gap-1.5 text-xs text-blue-400">
              <span>🌐</span>
              <span className="truncate">{websiteDisplay}</span>
            </div>
          )}
        </div>

        {/* Sub-scores */}
        {score && (
          <>
            <div className="border-t border-slate-800" />
            <div className="px-4 py-3 space-y-2">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
                Automation Readiness
              </span>
              <div className="space-y-1.5 pt-0.5">
                <ScoreBar label="CRM" score={score.crm_score} />
                <ScoreBar label="Scheduling" score={score.scheduling_score} />
                <ScoreBar label="Marketing" score={score.marketing_score} />
                <ScoreBar label="Invoicing" score={score.invoicing_score} />
              </div>
            </div>
          </>
        )}

        {/* Key signals */}
        {score?.key_signals?.length > 0 && (
          <>
            <div className="border-t border-slate-800" />
            <div className="px-4 py-2.5">
              <div className="flex flex-wrap gap-1">
                {score.key_signals.map((signal, i) => (
                  <span
                    key={i}
                    className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700/60"
                  >
                    {signal}
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        {/* AI summary */}
        {score?.summary && (
          <>
            <div className="border-t border-slate-800" />
            <div className="px-4 py-2.5">
              <p className="text-xs text-slate-400 leading-relaxed line-clamp-3 italic">
                &ldquo;{score.summary}&rdquo;
              </p>
            </div>
          </>
        )}

        {/* Deal value footer */}
        {score?.estimated_deal_value && (
          <div className="px-4 py-2 bg-slate-800/60 border-t border-slate-800 flex items-center justify-between">
            <span className="text-[10px] text-slate-500 uppercase tracking-wide font-medium">
              Deal potential
            </span>
            <span
              className={`text-xs font-semibold capitalize ${dealColors[score.estimated_deal_value] ?? 'text-slate-300'}`}
            >
              {score.estimated_deal_value}
            </span>
          </div>
        )}

        {/* Promote button */}
        <div className="px-4 py-2.5 border-t border-slate-800" style={{ pointerEvents: 'auto' }}>
          <button
            onClick={handlePromote}
            disabled={promoting || promoted || b.has_lead}
            className={`w-full text-xs font-semibold py-1.5 rounded-lg transition-colors ${
              promoted || b.has_lead
                ? 'bg-green-900/40 text-green-400 cursor-default'
                : 'bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-50'
            }`}
          >
            {promoting ? 'Adding…' : (promoted || b.has_lead) ? '✓ In Leads' : '+ Add to Leads'}
          </button>
        </div>
      </div>
    </div>
  )
}
