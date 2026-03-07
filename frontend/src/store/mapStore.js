import { create } from 'zustand'
import { toast } from '../components/ui/toast'
import { businessesApi } from '../api/businesses'

export const useMapStore = create((set) => ({
  mapCenter: [-118.2437, 34.0522], // Default: LA
  mapZoom: 11,
  searchCenter: null,
  searchRadiusMeters: 8047,
  markers: [],
  selectedBusiness: null,
  hoveredBusiness: null,
  hoverPosition: null,
  isLoadingMarkers: false,

  // Click-to-scan mode: active when search panel is open and no scan is running
  clickModeActive: false,
  // Coordinates set by clicking the map in click mode: [lng, lat] | null
  mapClickCenter: null,

  setMapCenter: (center) => set({ mapCenter: center }),
  setMapZoom: (zoom) => set({ mapZoom: zoom }),
  setSearchCenter: (center) => set({ searchCenter: center }),
  setSearchRadius: (radius) => set({ searchRadiusMeters: Math.min(radius, 50000) }),
  setSelectedBusiness: (business) => set({ selectedBusiness: business }),
  setHoveredBusiness: (business, position) => set({ hoveredBusiness: business, hoverPosition: position }),
  setClickMode: (active) => set({ clickModeActive: active }),
  setMapClickCenter: (center) => set({ mapClickCenter: center }),

  loadMarkersForScan: async (scanId) => {
    set({ isLoadingMarkers: true })
    try {
      const { data } = await businessesApi.mapData(scanId)
      set({ markers: data, isLoadingMarkers: false })
    } catch {
      set({ isLoadingMarkers: false })
      toast.error('Failed to load map markers')
    }
  },

  clearMarkers: () => set({ markers: [], selectedBusiness: null, hoveredBusiness: null, hoverPosition: null }),
}))
