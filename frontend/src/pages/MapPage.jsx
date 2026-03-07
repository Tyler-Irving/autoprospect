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
  const [isMobile, setIsMobile] = useState(false)
  const [mobilePane, setMobilePane] = useState('filters')
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

  useEffect(() => {
    const media = window.matchMedia('(max-width: 767px)')
    const sync = () => setIsMobile(media.matches)
    sync()
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

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

  const showFiltersPane = !isMobile || mobilePane === 'filters'
  const showMapPane = !isMobile || mobilePane === 'map'

  return (
    <div className="flex h-screen overflow-hidden flex-col md:flex-row">
      {isMobile && (
        <div className="px-4 pt-3 pb-2 shrink-0" style={{ background: 'var(--card)', borderBottom: '1px solid var(--border)' }}>
          <div className="grid grid-cols-2 gap-2 p-1 rounded-lg" style={{ background: 'var(--secondary)' }}>
            <button
              onClick={() => setMobilePane('filters')}
              className="h-8 rounded-md text-xs font-medium transition-colors cursor-pointer"
              style={
                mobilePane === 'filters'
                  ? { background: 'var(--card)', color: 'var(--foreground)', border: '1px solid var(--border)' }
                  : { color: 'var(--muted-foreground)' }
              }
            >
              Filters
            </button>
            <button
              onClick={() => setMobilePane('map')}
              className="h-8 rounded-md text-xs font-medium transition-colors cursor-pointer"
              style={
                mobilePane === 'map'
                  ? { background: 'var(--card)', color: 'var(--foreground)', border: '1px solid var(--border)' }
                  : { color: 'var(--muted-foreground)' }
              }
            >
              Map
            </button>
          </div>
        </div>
      )}

      {/* Left panel */}
      {showFiltersPane && (
        <div
          className={`${isMobile ? 'w-full flex-1' : hasResults ? 'w-80 flex-shrink-0' : 'w-72 flex-shrink-0'} flex flex-col p-4 overflow-y-auto transition-[width] duration-300`}
          style={{ background: 'var(--card)', borderRight: isMobile ? 'none' : '1px solid var(--border)' }}
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
                onClick={() => {
                  setShowSearch((v) => !v)
                  if (isMobile && !showSearch) setMobilePane('filters')
                }}
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
      )}

      {/* Map — clicking it closes the drawer */}
      {showMapPane && (
        <div
          className="flex-1 relative min-h-0"
          onClick={() => !clickModeActive && selectedBusiness && setSelectedBusiness(null)}
        >
          <MapView />

          {/* Mobile: floating "New search" button when viewing the map pane */}
          {isMobile && (
            <button
              onClick={(e) => { e.stopPropagation(); setMobilePane('filters') }}
              className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-1.5 text-xs font-medium rounded-full px-4 py-2 shadow-lg"
              style={{ background: '#f97316', color: '#fff', zIndex: 10 }}
            >
              <svg width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
              </svg>
              {hasResults ? 'New search' : 'Start a search'}
            </button>
          )}
        </div>
      )}

      {/* Hover card + drawer should only be visible when map is visible on mobile */}
      {showMapPane && (
        <>
          <BusinessHoverCard />
          <BusinessDetailDrawer
            promoting={promoting}
            promoted={promoted}
            onPromote={handlePromote}
          />
        </>
      )}
    </div>
  )
}
