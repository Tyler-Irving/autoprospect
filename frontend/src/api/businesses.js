import client from './client'

export const businessesApi = {
  list: (params = {}) => client.get('/businesses/', { params }),
  get: (id) => client.get(`/businesses/${id}/`),
  mapData: (scanId) => client.get('/businesses/map-data/', { params: { scan: scanId } }),
  promote: (id) => client.post(`/businesses/${id}/promote/`),
  enrichTier2: (id) => client.post(`/businesses/${id}/enrich-tier2/`),
}
