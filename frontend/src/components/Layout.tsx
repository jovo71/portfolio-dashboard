import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, TrendingUp, Receipt,
  Server, LogOut, Sun, Moon, BarChart3, Plus, Pencil, Trash2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { usePortfolio } from '../PortfolioContext'
import { categoriesApi } from '../api'
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
  const { categories, selectedCategoryId, setSelectedCategoryId, reload } = usePortfolio()

  function logout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  async function addCategory() {
    const name = window.prompt('Naam van de nieuwe categorie:')
    if (!name?.trim()) return
    try {
      const r = await categoriesApi.create(name.trim())
      await reload()
      setSelectedCategoryId(r.data.id)
      toast.success('Categorie aangemaakt')
    } catch {
      toast.error('Aanmaken mislukt')
    }
  }

  async function renameCategory() {
    if (selectedCategoryId == null) return
    const current = categories.find(c => c.id === selectedCategoryId)
    const name = window.prompt('Nieuwe naam:', current?.name)
    if (!name?.trim()) return
    try {
      await categoriesApi.rename(selectedCategoryId, name.trim())
      await reload()
    } catch {
      toast.error('Hernoemen mislukt')
    }
  }

  async function deleteCategory() {
    if (selectedCategoryId == null) return
    const current = categories.find(c => c.id === selectedCategoryId)
    if (!window.confirm(`Categorie "${current?.name}" verwijderen?`)) return
    try {
      await categoriesApi.delete(selectedCategoryId)
      await reload()
      toast.success('Categorie verwijderd')
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
          <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Categorie
          </label>
          <select
            className="form-control"
            style={{ fontSize: 13 }}
            value={selectedCategoryId ?? ''}
            onChange={e => setSelectedCategoryId(Number(e.target.value))}
          >
            {categories.length === 0 && <option value="">Laden…</option>}
            {categories.map(c => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <div style={{ display: 'flex', gap: 4 }}>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={addCategory} title="Nieuwe categorie">
              <Plus size={13} />
            </button>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={renameCategory} title="Hernoemen" disabled={selectedCategoryId == null}>
              <Pencil size={13} />
            </button>
            <button className="btn btn-secondary btn-sm btn-icon" onClick={deleteCategory} title="Verwijderen" disabled={selectedCategoryId == null}>
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
