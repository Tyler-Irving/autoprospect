export default function LoginPage() {
  const handleGitHubLogin = () => {
    // Generate a random state value for CSRF protection
    const state = crypto.randomUUID()
    sessionStorage.setItem('oauth_state', state)

    const params = new URLSearchParams({
      client_id: import.meta.env.VITE_GITHUB_CLIENT_ID,
      redirect_uri: `${window.location.origin}/auth/callback`,
      scope: 'user:email',
      state,
    })
    window.location.href = `https://github.com/login/oauth/authorize?${params}`
  }

  return (
    <div
      className="h-screen flex items-center justify-center"
      style={{ background: 'var(--background)' }}
    >
      <div
        className="w-full max-w-sm rounded-2xl p-8 flex flex-col items-center gap-6"
        style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
      >
        {/* Logo */}
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg"
          style={{ background: '#f97316' }}
        >
          AP
        </div>

        <div className="text-center space-y-1">
          <h1 className="text-lg font-semibold" style={{ color: 'var(--foreground)' }}>
            AutoProspect
          </h1>
          <p className="text-sm" style={{ color: 'var(--muted-foreground)' }}>
            Sign in to continue
          </p>
        </div>

        <button
          onClick={handleGitHubLogin}
          className="w-full flex items-center justify-center gap-3 py-2.5 px-4 rounded-lg font-medium text-sm transition-opacity hover:opacity-90"
          style={{ background: 'var(--foreground)', color: 'var(--background)' }}
        >
          <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.44 9.8 8.2 11.38.6.1.82-.26.82-.58v-2.02c-3.34.72-4.04-1.6-4.04-1.6-.54-1.38-1.32-1.74-1.32-1.74-1.08-.74.08-.72.08-.72 1.2.08 1.82 1.22 1.82 1.22 1.06 1.82 2.8 1.3 3.48.98.1-.76.42-1.28.76-1.58-2.66-.3-5.46-1.33-5.46-5.93 0-1.3.47-2.38 1.24-3.22-.12-.3-.54-1.52.12-3.18 0 0 1-.32 3.3 1.24a11.5 11.5 0 0 1 3-.4c1.02.004 2.04.14 3 .4 2.28-1.56 3.28-1.24 3.28-1.24.66 1.66.24 2.88.12 3.18.78.84 1.24 1.92 1.24 3.22 0 4.6-2.8 5.62-5.48 5.92.44.38.82 1.1.82 2.22v3.3c0 .32.22.7.82.58C20.56 21.8 24 17.3 24 12c0-6.63-5.37-12-12-12z" />
          </svg>
          Sign in with GitHub
        </button>

        <p className="text-xs text-center" style={{ color: 'var(--muted-foreground)' }}>
          Your data is private to your account.
        </p>
      </div>
    </div>
  )
}
