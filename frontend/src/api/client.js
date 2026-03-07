import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: { 'Content-Type': 'application/json' },
})

// Inject JWT on every request
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401: attempt token refresh once, then retry. On failure, log out.
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const store = useAuthStore.getState()

    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      const { refreshToken } = store
      if (refreshToken) {
        try {
          const { data } = await axios.post(
            `${client.defaults.baseURL}/auth/refresh/`,
            { refresh: refreshToken }
          )
          store.setAccessToken(data.access)
          error.config.headers.Authorization = `Bearer ${data.access}`
          return client(error.config)
        } catch {
          store.logout()
          window.location.href = '/login'
          return Promise.reject(error)
        }
      }
      store.logout()
      window.location.href = '/login'
    }

    return Promise.reject(error)
  }
)

export default client
