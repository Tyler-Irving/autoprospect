import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { agentApi } from '../api/agent'

export const useAgentStore = create(
  persist(
    (set, get) => ({
      config: null,
      isLoading: false,
      hasLoaded: false,
      schedules: [],
      schedulesLoaded: false,

      fetchConfig: async () => {
        if (get().isLoading) return
        set({ isLoading: true })
        try {
          const { data } = await agentApi.getConfig()
          set({ config: data, hasLoaded: true })
        } catch {
          set({ hasLoaded: true })
        } finally {
          set({ isLoading: false })
        }
      },

      updateConfig: async (patch) => {
        const { data } = await agentApi.updateConfig(patch)
        set({ config: data })
        return data
      },

      completeOnboarding: async () => {
        const { data } = await agentApi.completeOnboarding()
        set({ config: data })
        return data
      },

      setPaused: async (is_paused) => {
        const { data } = await agentApi.setPaused(is_paused)
        set((state) => ({ config: { ...state.config, is_paused: data.is_paused } }))
        return data
      },

      fetchSchedules: async () => {
        const { data } = await agentApi.listSchedules()
        const list = data.results ?? data
        set({ schedules: list, schedulesLoaded: true })
      },

      createSchedule: async (payload) => {
        const { data } = await agentApi.createSchedule(payload)
        set((s) => ({ schedules: [...s.schedules, data] }))
        return data
      },

      updateSchedule: async (id, patch) => {
        const { data } = await agentApi.updateSchedule(id, patch)
        set((s) => ({ schedules: s.schedules.map((sc) => (sc.id === id ? data : sc)) }))
        return data
      },

      deleteSchedule: async (id) => {
        await agentApi.deleteSchedule(id)
        set((s) => ({ schedules: s.schedules.filter((sc) => sc.id !== id) }))
      },

      runNow: async (id) => {
        const { data } = await agentApi.runNow(id)
        return data
      },

      reset: () => set({ config: null, hasLoaded: false, schedules: [], schedulesLoaded: false }),
    }),
    {
      name: 'autoprospect-agent',
      partialize: (state) => ({ config: state.config }),
    }
  )
)
