import { create } from 'zustand'
import toast from 'react-hot-toast'
import { businessesApi } from '../api/businesses'

export const useMapStore = create((set) => ({
  mapCenter: [-118.2437, 34.0522], // Default: LA
  mapZoom: 11,
  searchCenter: null,
  searchRadiusMeters: 8000,
  markers: [],
  selectedBusiness: null,
  hoveredBusiness: null,
  hoverPosition: null,
  isLoadingMarkers: false,

  setMapCenter: (center) => set({ mapCenter: center }),
  setMapZoom: (zoom) => set({ mapZoom: zoom }),
  setSearchCenter: (center) => set({ searchCenter: center }),
  setSearchRadius: (radius) => set({ searchRadiusMeters: radius }),
  setSelectedBusiness: (business) => set({ selectedBusiness: business }),
  setHoveredBusiness: (business, position) => set({ hoveredBusiness: business, hoverPosition: position }),

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

  clearMarkers: () => set({ markers: [], selectedBusiness: null }),
}))
