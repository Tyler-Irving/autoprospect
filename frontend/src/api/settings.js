import client from './client'

export const settingsApi = {
  get: () => client.get('/settings/'),
  patch: (data) => client.patch('/settings/', data),
}
