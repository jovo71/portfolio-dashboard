import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, TrendingUp, Receipt,
  Server, LogOut, Sun, Moon, BarChart3, Plus, Pencil, Trash2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { usePortfolio } from '../PortfolioContext'
import { portfoliosApi } from '../api'
import styles from './Layout.module.css'

interface Props {
  theme: 'dark' | 'light'
  toggleTheme: () => void
}

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/portfolio', icon: Briefcase, label: 'Portfolio' },
  { to: '/dividend', icon: TrendingUp, label: 'Dividend' },
  { to: '/kosten', icon: Receipt, label: 'Kosten' },
  { to: '/systeem', icon: Server, label: 'Systeemstatus' },
]

export default function Layout({ theme, toggleTheme }: Props) {
  const navigate = useNavigate()
  const { portfolios, selectedId, setSelectedId, reload } = usePortfolio()

  function logout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  async function addPortfolio() {
    const name = window.prompt('Naam van het nieuwe portfolio:')
    if (!name?.trim()) return
    try {
      const r = await portfoliosApi.create(name.trim())
      await reload()
      setSelectedId(r.data.id)
      toast.success('Portfolio aangemaakt')
    } catch {
      toast.error('Aanmaken mislukt')
    }
  }

  async function renamePortfolio() {
    if (selectedId == null) return
    const current = portfolios.find(p => p.id === selectedId)
    const name = window.prompt('Nieuwe naam:', current?.name)
    if (!name?.trim()) return
    try {
      await portfoliosApi.rename(selectedId, name.trim())
      await reload()
    } catch {
      toast.error('Hernoemen mislukt')
    }
  }

  async function deletePortfolio() {
    if (selectedId == null) return
    const current = portfolios.find(p => p.id === selectedId)
    if (!window.confirm(`Portfolio "${current?.name}" verwijderen?`)) return
    try {
      await portfoliosApi.delete(selectedId)
      await reload()
      toast.success('Portfolio verwijderd')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Verwijderen mislukt')
    }
  }

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <BarChart3 size={22} color="var(--accent-blue)" />
          <span>Portfolio</span>
        </div>

        <div style={{ padding: '0 12px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <select
            className="form-control"
            style={{ fontSize: 13 }}
            value={selectedId ?? ''}
            onChange={e => setSelectedId(Number(e.target.value))}
          >
            {portfolios.length === 0 && <option value="">Laden…</option>}
            {portfolios.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <div style={{ display: 'flex', gap: 4 }}>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={addPortfolio} title="Nieuw portfolio">
              <Plus size={13} />
            </button>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={renamePortfolio} title="Hernoemen" disabled={selectedId == null}>
              <Pencil size={13} />
            </button>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={deletePortfolio} title="Verwijderen" disabled={selectedId == null}>
              <Trash2 size={13} />
            </button>
          </div>
        </div>

        <nav className={styles.nav}>
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `${styles.navItem} ${isActive ? styles.active : ''}`
              }
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <button className={styles.iconBtn} onClick={toggleTheme} title="Thema wisselen">
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <button className={styles.iconBtn} onClick={logout} title="Uitloggen">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  )
}
