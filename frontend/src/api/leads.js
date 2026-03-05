import client from './client'

export const leadsApi = {
  create: (data) => client.post('/leads/', data),
  list: (params = {}) => client.get('/leads/', { params }),
  get: (id) => client.get(`/leads/${id}/`),
  update: (id, data) => client.patch(`/leads/${id}/`, data),
  delete: (id) => client.delete(`/leads/${id}/`),
  generateOutreach: (id) => client.post(`/leads/${id}/generate-outreach/`),
  activities: (id) => client.get(`/leads/${id}/activities/`),
  bulkAction: (data) => client.post('/leads/bulk-action/', data),

  // Lead Lists
  createList: (data) => client.post('/lead-lists/', data),
  getLists: () => client.get('/lead-lists/'),
  updateList: (id, data) => client.patch(`/lead-lists/${id}/`, data),
  deleteList: (id) => client.delete(`/lead-lists/${id}/`),
  addLeadsToList: (id, leadIds) => client.post(`/lead-lists/${id}/add-leads/`, { lead_ids: leadIds }),
}
