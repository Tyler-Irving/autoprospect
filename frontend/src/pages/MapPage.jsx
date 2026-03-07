import { useState, useEffect } from 'react'
import { useToasts } from '@/components/ui/toast'
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
  const { markers, selectedBusiness, setSelectedBusiness, setClickMode, clickModeActive } = useMapStore()
  const { promoteBusiness } = useLeadStore()
  const toasts = useToasts()
  const [showSearch, setShowSearch] = useState(true)
  const [promoting, setPromoting] = useState({})
  const [promoted, setPromoted] = useState({})

  const hasResults = activeScan?.status === 'completed' && markers.length > 0
  const isRunning = activeScan && !['completed', 'failed'].includes(activeScan.status)

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

  // Activate click-to-scan mode while the search panel is visible and no scan is running.
  // Automatically deactivates when a scan starts (isRunning becomes true).
  useEffect(() => {
    setClickMode(showSearch && !isRunning)
  }, [showSearch, isRunning])

  const handlePromote = async (business) => {
    if (promoting[business.id] || promoted[business.id] || business.has_lead) return
    setPromoting((p) => ({ ...p, [business.id]: true }))
    try {
      await promoteBusiness(business.id)
      setPromoted((p) => ({ ...p, [business.id]: true }))
      toasts.success(`${business.name} added to leads`)
    } catch {
      toasts.error('Failed to add lead')
    } finally {
      setPromoting((p) => ({ ...p, [business.id]: false }))
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left panel */}
      <div
        className={`${hasResults ? 'w-80' : 'w-72'} flex-shrink-0 flex flex-col p-4 overflow-hidden transition-[width] duration-300`}
        style={{ background: 'var(--card)', borderRight: '1px solid var(--border)' }}
      >
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div>
            <h1 className="text-sm font-semibold leading-tight" style={{ color: 'var(--foreground)' }}>
              {hasResults ? (activeScan?.label || 'Scan Results') : 'Prospect Scanner'}
            </h1>
            {!hasResults && !isRunning && (
              <p className="text-[11px] mt-0.5" style={{ color: 'var(--muted-foreground)' }}>
                Search or click the map to begin
              </p>
            )}
          </div>
          {hasResults && (
            <button
              onClick={() => setShowSearch((v) => !v)}
              className="text-[10px] transition-colors hover:text-[#fafafa] cursor-pointer"
              style={{ color: 'var(--muted-foreground)' }}
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
        onClick={() => !clickModeActive && selectedBusiness && setSelectedBusiness(null)}
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
