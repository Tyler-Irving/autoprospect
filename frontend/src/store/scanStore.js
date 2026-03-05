import { create } from 'zustand'
import { scansApi } from '../api/scans'
import { SCAN_POLL_INTERVAL_MS, SCAN_TERMINAL_STATUSES } from '../utils/constants'

export const useScanStore = create((set, get) => ({
  scans: [],
  activeScan: null,
  isLaunching: false,
  pollTimer: null,

  loadScans: async () => {
    const { data } = await scansApi.list()
    set({ scans: data.results || data })
  },

  launchScan: async (params) => {
    set({ isLaunching: true })
    try {
      const { data: scan } = await scansApi.create(params)
      set((state) => ({
        scans: [scan, ...state.scans],
        activeScan: scan,
        isLaunching: false,
      }))
      get().startPolling(scan.id)
      return scan
    } catch (err) {
      set({ isLaunching: false })
      throw err
    }
  },

  startPolling: (scanId) => {
    get().stopPolling()
    const timer = setInterval(async () => {
      try {
        const { data: scan } = await scansApi.get(scanId)
        set((state) => ({
          activeScan: scan,
          scans: state.scans.map((s) => (s.id === scanId ? scan : s)),
        }))
        if (SCAN_TERMINAL_STATUSES.includes(scan.status)) {
          get().stopPolling()
        }
      } catch {
        get().stopPolling()
      }
    }, SCAN_POLL_INTERVAL_MS)
    set({ pollTimer: timer })
  },

  stopPolling: () => {
    const { pollTimer } = get()
    if (pollTimer) {
      clearInterval(pollTimer)
      set({ pollTimer: null })
    }
  },

  setActiveScan: (scan) => set({ activeScan: scan }),
}))
