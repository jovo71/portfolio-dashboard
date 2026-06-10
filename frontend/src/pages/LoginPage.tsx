import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, Eye, EyeOff } from 'lucide-react'
import { authApi } from '../api'
import toast from 'react-hot-toast'
import styles from './LoginPage.module.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const resp = await authApi.login(username, password)
      localStorage.setItem('token', resp.data.access_token)
      navigate('/')
    } catch {
      toast.error('Onjuiste gebruikersnaam of wachtwoord')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <BarChart3 size={36} color="var(--accent-blue)" />
          <h1>Portfolio Dashboard</h1>
          <p>Inloggen om door te gaan</p>
        </div>

        <form onSubmit={handleLogin} className={styles.form}>
          <div className="form-group">
            <label className="form-label">Gebruikersnaam</label>
            <input
              className="form-control"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="admin"
              autoFocus
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Wachtwoord</label>
            <div className={styles.pwWrap}>
              <input
                className="form-control"
                type={showPw ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                className={styles.eyeBtn}
                onClick={() => setShowPw(v => !v)}
              >
                {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', justifyContent: 'center', padding: '10px' }}
          >
            {loading ? 'Inloggen...' : 'Inloggen'}
          </button>
        </form>
      </div>
    </div>
  )
}
