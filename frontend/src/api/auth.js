import client from './client'
import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export const authApi = {
  // Exchange GitHub OAuth code for JWT tokens
  githubLogin: (code, redirectUri) =>
    axios.post(`${BASE}/auth/github/`, { code, redirect_uri: redirectUri }),

  // Get current user info (requires auth)
  me: () => client.get('/auth/me/'),
}
