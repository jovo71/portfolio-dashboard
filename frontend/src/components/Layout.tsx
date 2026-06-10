import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Briefcase, TrendingUp, Receipt,
  Server, LogOut, Sun, Moon, BarChart3
} from 'lucide-react'
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

  function logout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <div className={styles.root}>
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <BarChart3 size={22} color="var(--accent-blue)" />
          <span>Portfolio</span>
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
