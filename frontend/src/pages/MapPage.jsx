import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import MapView from '../components/Map/MapView'
import SearchControls from '../components/Map/SearchControls'
import BusinessHoverCard from '../components/Map/BusinessHoverCard'
import BusinessDetailDrawer from '../components/Map/BusinessDetailDrawer'
import ScanProgress from '../components/Scan/ScanProgress'
import ScanResults from '../components/Scan/ScanResults'
import { useScanStore } from '../store/scanStore'
import { useMapStore } from '../store/mapStore'
import { useLeadStore } from '../store/leadStore'

export default function MapPage() {
  const { activeScan } = useScanStore()
  const { markers, selectedBusiness, setSelectedBusiness } = useMapStore()
  const { promoteBusiness } = useLeadStore()
  const [showSearch, setShowSearch] = useState(true)
  const [promoting, setPromoting] = useState({})
  const [promoted, setPromoted] = useState({})

  const hasResults = activeScan?.status === 'completed' && markers.length > 0

  // Auto-collapse search when results arrive; re-open on new scan start
  useEffect(() => {
    if (hasResults) setShowSearch(false)
  }, [hasResults])

  useEffect(() => {
    if (activeScan?.status === 'discovering') setShowSearch(true)
  }, [activeScan?.status])

  // Reset promote state when a new scan starts so stale promoted flags
  // from a previous scan don't carry over to the new results.
  useEffect(() => {
    setPromoting({})
    setPromoted({})
  }, [activeScan?.id])

  const handlePromote = async (business) => {
    if (promoting[business.id] || promoted[business.id] || business.has_lead) return
    setPromoting((p) => ({ ...p, [business.id]: true }))
    try {
      await promoteBusiness(business.id)
      setPromoted((p) => ({ ...p, [business.id]: true }))
      toast.success(`${business.name} added to leads`)
    } catch {
      toast.error('Failed to add lead')
    } finally {
      setPromoting((p) => ({ ...p, [business.id]: false }))
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left panel */}
      <div className={`${hasResults ? 'w-80' : 'w-72'} flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col p-4 overflow-hidden transition-[width] duration-300`}>
        <div className="flex items-center justify-between mb-4 shrink-0">
          <h1 className="text-sm font-semibold text-slate-200">AutoProspect</h1>
          {hasResults && (
            <button
              onClick={() => setShowSearch((v) => !v)}
              className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
            >
              {showSearch ? 'Hide search' : 'New search'}
            </button>
          )}
        </div>

        {(!hasResults || showSearch) && (
          <div className="shrink-0">
            <SearchControls />
          </div>
        )}

        <div className="shrink-0">
          <ScanProgress />
        </div>

        {hasResults && (
          <ScanResults
            promoting={promoting}
            promoted={promoted}
            onPromote={handlePromote}
          />
        )}
      </div>

      {/* Map — clicking it closes the drawer */}
      <div
        className="flex-1 relative"
        onClick={() => selectedBusiness && setSelectedBusiness(null)}
      >
        <MapView />
      </div>

      {/* Hover card */}
      <BusinessHoverCard />

      {/* Detail drawer — fixed to right viewport edge */}
      <BusinessDetailDrawer
        promoting={promoting}
        promoted={promoted}
        onPromote={handlePromote}
      />
    </div>
  )
}
