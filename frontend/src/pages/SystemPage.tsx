import { useState, useEffect } from 'react'
import { RefreshCw, CheckCircle, XCircle, Clock, Server } from 'lucide-react'
import toast from 'react-hot-toast'
import { systemApi, pricesApi, SystemStatus } from '../api'
import { format } from 'date-fns'
import { nl } from 'date-fns/locale'

export default function SystemPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  async function load() {
    try {
      const resp = await systemApi.status()
      setStatus(resp.data)
    } catch { toast.error('Systeemstatus ophalen mislukt') }
    finally { setLoading(false) }
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

  useEffect(() => {
    load()
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
        <button className="btn btn-secondary btn-sm" onClick={refreshPrices} disabled={refreshing}>
          <RefreshCw size={14} style={{ animation: refreshing ? 'spin 0.8s linear infinite' : 'none' }} />
          Koersen verversen
        </button>
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
