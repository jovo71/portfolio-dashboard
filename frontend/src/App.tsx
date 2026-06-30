import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import { PortfolioProvider } from './PortfolioContext'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import PortfolioPage from './pages/PortfolioPage'
import DividendPage from './pages/DividendPage'
import CostsPage from './pages/CostsPage'
import SystemPage from './pages/SystemPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    return (localStorage.getItem('theme') as 'dark' | 'light') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <PortfolioProvider>
              <Layout theme={theme} toggleTheme={() => setTheme(t => t === 'dark' ? 'light' : 'dark')} />
            </PortfolioProvider>
          </RequireAuth>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="dividend" element={<DividendPage />} />
        <Route path="kosten" element={<CostsPage />} />
        <Route path="systeem" element={<SystemPage />} />
      </Route>
    </Routes>
  )
}
