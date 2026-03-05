import { create } from 'zustand'
import { leadsApi } from '../api/leads'
import { businessesApi } from '../api/businesses'
import { useMapStore } from './mapStore'

export const useLeadStore = create((set, get) => ({
  leads: [],
  selectedLead: null,
  isLoading: false,
  filters: { status: '', minScore: '', search: '' },

  setFilters: (filters) => set((state) => ({ filters: { ...state.filters, ...filters } })),

  fetchLeads: async () => {
    set({ isLoading: true })
    try {
      const { filters } = get()
      const params = {}
      if (filters.status) params.status = filters.status
      if (filters.minScore) params.min_score = filters.minScore
      const { data } = await leadsApi.list(params)
      set({ leads: data.results ?? data, isLoading: false })
    } catch {
      set({ isLoading: false })
    }
  },

  fetchLead: async (id) => {
    const { data } = await leadsApi.get(id)
    set({ selectedLead: data })
    return data
  },

  promoteBusiness: async (businessId) => {
    const { data } = await businessesApi.promote(businessId)
    // Reflect the new lead status in the map markers so that re-hovering
    // the same business shows "In Leads" without requiring a full marker reload.
    useMapStore.setState((state) => ({
      markers: state.markers.map((m) =>
        m.id === businessId ? { ...m, has_lead: true } : m
      ),
    }))
    return data
  },

  updateLead: async (id, patch) => {
    const { data } = await leadsApi.update(id, patch)
    set((state) => ({
      leads: state.leads.map((l) => (l.id === id ? { ...l, ...data } : l)),
      selectedLead: state.selectedLead?.id === id ? { ...state.selectedLead, ...data } : state.selectedLead,
    }))
    return data
  },

  deleteLead: async (id) => {
    await leadsApi.delete(id)
    set((state) => ({
      leads: state.leads.filter((l) => l.id !== id),
      selectedLead: state.selectedLead?.id === id ? null : state.selectedLead,
    }))
  },

  clearSelected: () => set({ selectedLead: null }),
}))
