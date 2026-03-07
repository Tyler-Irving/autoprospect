import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Sidebar from './components/common/Sidebar'
import MapPage from './pages/MapPage'
import LeadsPage from './pages/LeadsPage'
import LeadDetailPage from './pages/LeadDetailPage'
import ScansPage from './pages/ScansPage'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{ style: { background: '#171717', color: '#fafafa' } }} />
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<MapPage />} />
            <Route path="/leads" element={<LeadsPage />} />
            <Route path="/leads/:id" element={<LeadDetailPage />} />
            <Route path="/scans" element={<ScansPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
