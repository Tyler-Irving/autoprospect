import client from './client'

export const agentApi = {
  getConfig: () => client.get('/agent/config/'),
  updateConfig: (data) => client.patch('/agent/config/', data),
  completeOnboarding: () => client.post('/agent/onboarding/complete/'),
  setPaused: (is_paused) => client.post('/agent/config/pause/', { is_paused }),

  // Schedules
  listSchedules: () => client.get('/agent/schedules/'),
  createSchedule: (data) => client.post('/agent/schedules/', data),
  updateSchedule: (id, data) => client.patch(`/agent/schedules/${id}/`, data),
  deleteSchedule: (id) => client.delete(`/agent/schedules/${id}/`),
  runNow: (id) => client.post(`/agent/schedules/${id}/run-now/`),
}
