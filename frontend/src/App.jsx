import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import { useAgentStore } from './store/agentStore'
import Sidebar from './components/common/Sidebar'
import MapPage from './pages/MapPage'
import LeadsPage from './pages/LeadsPage'
import LeadDetailPage from './pages/LeadDetailPage'
import ScansPage from './pages/ScansPage'
import SettingsPage from './pages/SettingsPage'
import AgentPage from './pages/AgentPage'
import OnboardingPage from './pages/OnboardingPage'
import LoginPage from './pages/LoginPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import FrenchHorn from './components/playground/FrenchHorn_2'

function ProtectedRoute({ children }) {
  const accessToken = useAuthStore((s) => s.accessToken)
  const config = useAgentStore((s) => s.config)
  const hasLoaded = useAgentStore((s) => s.hasLoaded)
  const fetchConfig = useAgentStore((s) => s.fetchConfig)
  const location = useLocation()

  useEffect(() => {
    if (accessToken && !hasLoaded) fetchConfig()
  }, [accessToken, hasLoaded, fetchConfig])

  if (!accessToken) return <Navigate to="/login" replace />
  if (!hasLoaded) return null

  // Redirect to onboarding unless already heading there
  if (!config?.is_configured && location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />
  }

  return children
}

function AppShell() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<ProtectedRoute><MapPage /></ProtectedRoute>} />
          <Route path="/leads" element={<ProtectedRoute><LeadsPage /></ProtectedRoute>} />
          <Route path="/leads/:id" element={<ProtectedRoute><LeadDetailPage /></ProtectedRoute>} />
          <Route path="/scans" element={<ProtectedRoute><ScansPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
          <Route path="/agent" element={<ProtectedRoute><AgentPage /></ProtectedRoute>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/french-horn-preview" element={<FrenchHorn />} />
        <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/*" element={<AppShell />} />
      </Routes>
    </BrowserRouter>
  )
}
