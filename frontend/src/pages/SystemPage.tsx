import { useState, useEffect } from 'react'
import { RefreshCw, CheckCircle, XCircle, Clock, Server, GitBranch, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import { systemApi, pricesApi, SystemStatus, VersionInfo } from '../api'
import { format } from 'date-fns'
import { nl } from 'date-fns/locale'

export default function SystemPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [version, setVersion] = useState<VersionInfo | null>(null)
  const [deploying, setDeploying] = useState(false)

  async function load() {
    try {
      const resp = await systemApi.status()
      setStatus(resp.data)
    } catch { toast.error('Systeemstatus ophalen mislukt') }
    finally { setLoading(false) }
  }

  async function loadVersion() {
    try {
      const resp = await systemApi.version()
      setVersion(resp.data)
    } catch { /* versiecontrole is optioneel; stilhouden */ }
  }

  async function refreshPrices() {
    setRefreshing(true)
    try {
      await pricesApi.refresh()
      toast.success('Koersen bijgewerkt')
      load()
    } catch { toast.error('Koersupdate mislukt') }
    finally { setRefreshing(false) }
  }

  async function deploy() {
    if (!window.confirm('Nieuwste versie ophalen en de applicatie opnieuw opstarten?')) return
    setDeploying(true)
    try {
      await systemApi.deploy()
      toast.success('Update gestart — de app wordt herstart…')
      waitForRestart()
    } catch { toast.error('Update starten mislukt'); setDeploying(false) }
  }

  // Wacht tot de backend daadwerkelijk herstart is (down → weer up)
  // en herlaad dan de pagina zodat de nieuw gebouwde frontend laadt.
  function waitForRestart() {
    let sawDown = false
    let attempts = 0
    const maxAttempts = 60 // ~2 minuten bij 2s interval
    const timer = setInterval(async () => {
      attempts++
      try {
        await systemApi.status()
        if (sawDown) {
          clearInterval(timer)
          toast.success('Update voltooid — pagina wordt herladen')
          setTimeout(() => window.location.reload(), 800)
        }
      } catch {
        sawDown = true // backend/nginx is even onbereikbaar tijdens de herstart
      }
      if (attempts >= maxAttempts) {
        clearInterval(timer)
        setDeploying(false)
        toast('Herlaad de pagina (F5) om de nieuwe versie te laden')
      }
    }, 2000)
  }

  useEffect(() => {
    load()
    loadVersion()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  function fmtDate(d?: string) {
    if (!d) return '—'
    try { return format(new Date(d), 'dd MMM yyyy HH:mm:ss', { locale: nl }) }
    catch { return d }
  }

  const eventTypeColor = (t: string) => {
    if (t.includes('success')) return 'var(--color-gain)'
    if (t.includes('error')) return 'var(--color-loss)'
    return 'var(--accent-orange)'
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1>Systeemstatus</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={refreshPrices} disabled={refreshing}>
            <RefreshCw size={14} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
            Koersen verversen
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={deploy}
            disabled={deploying}
            title={version?.update_available ? `${version.commits_behind} nieuwe commit(s) beschikbaar` : 'Nieuwste versie ophalen en herstarten'}
          >
            <Download size={14} style={{ animation: deploying ? 'spin 0.8s linear infinite' : 'none' }} />
            {deploying ? 'Bezig met bijwerken…' : 'App bijwerken'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /> Laden…</div>
      ) : status ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">API Status</span>
                <Server size={15} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <span className={`status-dot ${status.api_status === 'online' ? 'status-online' : 'status-offline'}`} />
                <span style={{ fontWeight: 600 }}>{status.api_status === 'online' ? 'Online' : 'Offline'}</span>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Scheduler</span>
                <Clock size={15} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <span className={`status-dot ${status.scheduler_running ? 'status-online' : 'status-offline'}`} />
                <span style={{ fontWeight: 600 }}>{status.scheduler_running ? 'Actief' : 'Gestopt'}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Updates: 08:00, 13:00</div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Succesvolle updates</span>
                <CheckCircle size={15} color="var(--color-gain)" />
              </div>
              <div className="metric-value gain" style={{ marginTop: 8 }}>{status.successful_updates}</div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Mislukte updates</span>
                <XCircle size={15} color="var(--color-loss)" />
              </div>
              <div className="metric-value loss" style={{ marginTop: 8 }}>{status.failed_updates}</div>
            </div>

            <div className="card" style={{ gridColumn: 'span 2' }}>
              <div className="card-header">
                <span className="card-title">Laatste update</span>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 15, marginTop: 8 }}>
                {fmtDate(status.last_update?.toString())}
              </div>
            </div>

            {version && (
              <div className="card" style={{ gridColumn: 'span 2' }}>
                <div className="card-header">
                  <span className="card-title">Softwareversie</span>
                  <GitBranch size={15} />
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 15 }}>
                    {version.current_commit} ({version.branch})
                  </span>
                  {version.update_available ? (
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-orange)' }}>
                      {version.commits_behind} update(s) beschikbaar
                    </span>
                  ) : (
                    <span style={{ fontSize: 12, color: 'var(--color-gain)' }}>Up-to-date</span>
                  )}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  {version.last_commit_message}
                </div>
              </div>
            )}
          </div>

          {/* Logboek */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Recente logboekregels</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {status.recent_logs.length === 0 ? (
                <p style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Geen logboekregels beschikbaar.</p>
              ) : status.recent_logs.map((log, i) => (
                <div key={i} style={{
                  display: 'flex', gap: 12, padding: '10px 14px',
                  background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)',
                  fontSize: 12,
                }}>
                  <span style={{ color: eventTypeColor(log.event_type), fontWeight: 600, minWidth: 160 }}>
                    {log.event_type}
                  </span>
                  <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', minWidth: 140 }}>
                    {fmtDate(log.timestamp)}
                  </span>
                  <span style={{ color: 'var(--text-secondary)' }}>{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
