import MapView from '../components/Map/MapView'
import SearchControls from '../components/Map/SearchControls'
import BusinessHoverCard from '../components/Map/BusinessHoverCard'
import ScanProgress from '../components/Scan/ScanProgress'

export default function MapPage() {
  return (
    <div className="flex h-screen">
      {/* Left panel: search controls */}
      <div className="w-72 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col p-4 overflow-y-auto">
        <h1 className="text-sm font-semibold text-slate-200 mb-4">AutoProspect</h1>
        <SearchControls />
        <ScanProgress />
      </div>

      {/* Map */}
      <div className="flex-1">
        <MapView />
      </div>

      {/* Hover card — fixed overlay, rendered outside map div so it's never clipped */}
      <BusinessHoverCard />
    </div>
  )
}
