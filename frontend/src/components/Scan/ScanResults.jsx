import { useMapStore } from '../../store/mapStore'
import { getScoreColor } from '../../utils/constants'

export default function ScanResults({ promoting, promoted, onPromote }) {
  const { markers, selectedBusiness, setSelectedBusiness } = useMapStore()

  if (!markers.length) return null

  const sorted = [...markers].sort((a, b) => {
    if (a.overall_score == null && b.overall_score == null) return 0
    if (a.overall_score == null) return 1
    if (b.overall_score == null) return -1
    return b.overall_score - a.overall_score
  })

  const highCount = markers.filter((m) => m.overall_score >= 70).length
  const medCount = markers.filter((m) => m.overall_score >= 40 && m.overall_score < 70).length

  return (
    <div className="flex-1 flex flex-col min-h-0 mt-4 gap-3">

      {/* Summary */}
      <div className="flex items-baseline justify-between shrink-0">
        <span className="text-xs font-semibold text-slate-300">{markers.length} businesses</span>
        <div className="flex gap-2 text-[10px]">
          {highCount > 0 && <span className="text-green-400 font-medium">{highCount} high</span>}
          {medCount > 0 && <span className="text-yellow-400 font-medium">{medCount} med</span>}
        </div>
      </div>

      {/* Scrollable list — fills all remaining panel height */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-1 pr-0.5">
        {sorted.map((business) => {
          const score = business.overall_score
          const scoreColor = getScoreColor(score)
          const isSelected = selectedBusiness?.id === business.id
          const isPromoted = promoted[business.id] || business.has_lead
          const isPromoting = promoting[business.id]
          const category = business.category?.replace(/_/g, ' ')

          return (
            <div
              key={business.id}
              onClick={() => setSelectedBusiness(isSelected ? null : business)}
              className={`flex items-center gap-2.5 px-2.5 py-2.5 rounded-lg cursor-pointer transition-colors border ${
                isSelected
                  ? 'bg-slate-700 border-slate-600'
                  : 'bg-slate-800/60 border-transparent hover:bg-slate-800 hover:border-slate-700'
              }`}
            >
              {/* Score badge */}
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold"
                style={{
                  background: score != null ? `${scoreColor}20` : '#1e293b',
                  color: score != null ? scoreColor : '#475569',
                  border: `1px solid ${score != null ? scoreColor + '40' : '#334155'}`,
                }}
              >
                {score ?? '—'}
              </div>

              {/* Name + meta */}
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-slate-200 truncate leading-snug">
                  {business.name}
                </div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  {category && (
                    <span className="text-[10px] text-slate-500 capitalize truncate">{category}</span>
                  )}
                  {isPromoted && (
                    <span className="text-[10px] text-green-500 font-medium shrink-0">In Leads</span>
                  )}
                </div>
              </div>

              {/* Quick promote button */}
              <button
                onClick={(e) => { e.stopPropagation(); onPromote(business) }}
                disabled={isPromoting || isPromoted}
                title={isPromoted ? 'Already in leads' : 'Add to leads'}
                className={`shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold transition-colors ${
                  isPromoted
                    ? 'text-green-500 bg-green-900/20 cursor-default'
                    : 'text-slate-500 bg-slate-700 hover:bg-blue-600 hover:text-white'
                }`}
              >
                {isPromoting ? '…' : isPromoted ? '✓' : '+'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
