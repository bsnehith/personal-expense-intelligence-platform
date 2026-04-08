import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'

const HomePage = lazy(() => import('./pages/HomePage'))
const LiveFeedPage = lazy(() => import('./pages/LiveFeedPage'))
const UploadPage = lazy(() => import('./pages/UploadPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const AnomaliesPage = lazy(() => import('./pages/AnomaliesPage'))
const CoachPage = lazy(() => import('./pages/CoachPage'))
const ModelPage = lazy(() => import('./pages/ModelPage'))

function PageFallback() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-content-muted">
      <div className="h-9 w-9 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      <p className="text-sm font-medium">Loading module…</p>
    </div>
  )
}

export default function App() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route index element={<HomePage />} />
        <Route path="app" element={<AppShell />}>
          <Route index element={<LiveFeedPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="anomalies" element={<AnomaliesPage />} />
          <Route path="coach" element={<CoachPage />} />
          <Route path="model" element={<ModelPage />} />
        </Route>
        <Route path="upload" element={<Navigate to="/app/upload" replace />} />
        <Route path="dashboard" element={<Navigate to="/app/dashboard" replace />} />
        <Route path="anomalies" element={<Navigate to="/app/anomalies" replace />} />
        <Route path="coach" element={<Navigate to="/app/coach" replace />} />
        <Route path="model" element={<Navigate to="/app/model" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
