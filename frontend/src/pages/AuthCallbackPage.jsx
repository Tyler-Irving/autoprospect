import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'

export default function AuthCallbackPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const didRun = useRef(false)

  useEffect(() => {
    // Strict mode / double-invoke guard
    if (didRun.current) return
    didRun.current = true

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')
    const storedState = sessionStorage.getItem('oauth_state')
    sessionStorage.removeItem('oauth_state')

    if (!code || state !== storedState) {
      navigate('/login', { replace: true })
      return
    }

    const redirectUri = `${window.location.origin}/auth/callback`
    authApi
      .githubLogin(code, redirectUri)
      .then(({ data }) => {
        setAuth(data.access, data.refresh, data.user)
        navigate('/', { replace: true })
      })
      .catch(() => navigate('/login', { replace: true }))
  }, [])

  return (
    <div
      className="h-screen flex items-center justify-center"
      style={{ background: 'var(--background)' }}
    >
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin"
          style={{ borderColor: '#f97316', borderTopColor: 'transparent' }}
        />
        <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
          Signing you in…
        </p>
      </div>
    </div>
  )
}
