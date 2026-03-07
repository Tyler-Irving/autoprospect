import client from './client'

export const scansApi = {
  create: (data) => client.post('/scans/', data),
  list: () => client.get('/scans/'),
  get: (id) => client.get(`/scans/${id}/`),
  delete: (id) => client.delete(`/scans/${id}/`),
  rerun: (id) => client.post(`/scans/${id}/rerun/`),
  getBusinesses: (id, params = {}) => client.get(`/scans/${id}/businesses/`, { params }),
  dashboardStats: () => client.get('/dashboard/stats/'),
}
