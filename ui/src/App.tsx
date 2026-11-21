import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { CasePage } from './pages/CasePage'
import { QueuePage } from './pages/QueuePage'
import { RunPage } from './pages/RunPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<QueuePage />} />
        <Route path="/case/:hitId" element={<CasePage />} />
        <Route path="/run" element={<RunPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}