import { useState, useEffect } from 'react'
import { RefreshCw, TrendingUp, TrendingDown, Wallet, Percent, PieChart } from 'lucide-react'
import {
  AreaChart, Area, LineChart, Line, PieChart as RPieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import toast from 'react-hot-toast'
import { performanceApi, pricesApi, PerformanceData } from '../api'
import { usePortfolio } from '../PortfolioContext'
import styles from './DashboardPage.module.css'
import { format } from 'date-fns'
import { nl } from 'date-fns/locale'

const PERIOD_OPTIONS = [
  { value: 'today', label: 'Vandaag' },
  { value: 'week', label: 'Deze week' },
  { value: 'month', label: 'Deze maand' },
  { value: 'ytd', label: 'Jaar tot heden' },
  { value: 'since_purchase', label: 'Sinds aankoop' },
  { value: 'custom', label: 'Aangepast' },
]

const CHART_COLORS = ['#388bfd', '#3fb950', '#bc8cff', '#ffa657', '#39d2c0', '#f85149', '#d29922']

function fmt(v: number, decimals = 0) {
  return new Intl.NumberFormat('nl-NL', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(v)
}

function fmtCurrency(v: number) {
  return new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(v)
}

function fmtPct(v: number) {
  const sign = v >= 0 ? '+' : ''
  return `${sign}${fmt(v, 2)}%`
}

export default function DashboardPage() {
  const [period, setPeriod] = useState('ytd')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [data, setData] = useState<PerformanceData | null>(null)
  const [history, setHistory] = useState<{ date: string; value: number }[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const { selectedId } = usePortfolio()

  async function loadData() {
    if (selectedId == null) return
    setLoading(true)
    try {
      const [perfResp, histResp] = await Promise.all([
        performanceApi.get(period, startDate || undefined, endDate || undefined, selectedId),
        performanceApi.history(365, selectedId),
      ])
      setData(perfResp.data)
      setHistory(histResp.data)
    } catch {
      toast.error('Fout bij laden van gegevens')
    } finally {
      setLoading(false)
    }
  }

  async function refreshPrices() {
    setRefreshing(true)
    try {
      await pricesApi.refresh()
      toast.success('Koersen bijgewerkt')
      setLastUpdate(new Date().toLocaleTimeString('nl-NL'))
      await loadData()
    } catch {
      toast.error('Koersen verversen mislukt')
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => { loadData() }, [period, startDate, endDate, selectedId])

  const s = data?.summary
  const isGain = (v?: number) => (v ?? 0) >= 0

  // Verdeling voor pie charts
  const allocationData = data?.investments.map(inv => ({
    name: inv.name.length > 15 ? inv.name.slice(0, 13) + '…' : inv.name,
    value: inv.current_value,
  })) ?? []

  const brokerData = (() => {
    const map: Record<string, number> = {}
    data?.investments.forEach(inv => {
      const b = inv.broker || 'Onbekend'
      map[b] = (map[b] || 0) + inv.current_value
    })
    return Object.entries(map).map(([name, value]) => ({ name, value }))
  })()

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className={styles.tooltip}>
        <div className={styles.tooltipLabel}>{label}</div>
        {payload.map((p: any, i: number) => (
          <div key={i} style={{ color: p.color }}>
            {p.name}: {fmtCurrency(p.value)}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <div>
          <h1>Dashboard</h1>
          {lastUpdate && <p className={styles.lastUpdate}>Laatste update: {lastUpdate}</p>}
        </div>
        <div className={styles.controls}>
          <select
            className="form-control"
            style={{ width: 'auto' }}
            value={period}
            onChange={e => setPeriod(e.target.value)}
          >
            {PERIOD_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          {period === 'custom' && (
            <>
              <input type="date" className="form-control" value={startDate} onChange={e => setStartDate(e.target.value)} />
              <input type="date" className="form-control" value={endDate} onChange={e => setEndDate(e.target.value)} />
            </>
          )}
          <button
            className="btn btn-secondary"
            onClick={refreshPrices}
            disabled={refreshing}
          >
            <RefreshCw size={14} className={refreshing ? styles.spinning : ''} />
            Koersen verversen
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /> Gegevens laden…</div>
      ) : s ? (
        <>
          {/* KPI kaarten */}
          <div className={styles.kpiGrid}>
            <div className="card">
              <div className="card-header">
                <span className="card-title">Portefeuillewaarde</span>
                <Wallet size={16} color="var(--accent-blue)" />
              </div>
              <div className={`metric-value`}>{fmtCurrency(s.total_value)}</div>
              <div className="metric-label">{s.num_investments} beleggingen</div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Koersrendement</span>
                {isGain(s.price_return)
                  ? <TrendingUp size={16} color="var(--color-gain)" />
                  : <TrendingDown size={16} color="var(--color-loss)" />}
              </div>
              <div className={`metric-value ${isGain(s.price_return) ? 'gain' : 'loss'}`}>
                {fmtCurrency(s.price_return)}
              </div>
              <div className="metric-label">
                <span className={`badge ${isGain(s.price_return_pct) ? 'badge-gain' : 'badge-loss'}`}>
                  {fmtPct(s.price_return_pct)}
                </span>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Totaalrendement</span>
                <Percent size={16} color="var(--accent-purple)" />
              </div>
              <div className={`metric-value ${isGain(s.total_return) ? 'gain' : 'loss'}`}>
                {fmtCurrency(s.total_return)}
              </div>
              <div className="metric-label">
                <span className={`badge ${isGain(s.total_return_pct) ? 'badge-gain' : 'badge-loss'}`}>
                  {fmtPct(s.total_return_pct)}
                </span>
                {' '}incl. dividend &amp; kosten
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Dividend ontvangen</span>
                <TrendingUp size={16} color="var(--color-gain)" />
              </div>
              <div className="metric-value gain">{fmtCurrency(s.dividend_return)}</div>
              <div className="metric-label">
                <span className="badge badge-gain">{fmtPct(s.dividend_return_pct)}</span>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Totale kosten</span>
                <Receipt size={16} color="var(--accent-orange)" />
              </div>
              <div className="metric-value" style={{ color: 'var(--accent-orange)' }}>
                {fmtCurrency(s.total_costs)}
              </div>
              <div className="metric-label">impact op rendement</div>
            </div>
          </div>

          {/* Grafieken */}
          <div className={styles.chartsGrid}>
            <div className="card" style={{ gridColumn: 'span 2' }}>
              <div className="card-header">
                <span className="card-title">Portefeuillewaarde — 1 jaar</span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={history}>
                  <defs>
                    <linearGradient id="portGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#388bfd" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#388bfd" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    tickFormatter={d => {
                      try { return format(new Date(d), 'MMM', { locale: nl }) } catch { return d }
                    }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    tickFormatter={v => `€${(v / 1000).toFixed(0)}k`} />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="value" name="Waarde"
                    stroke="#388bfd" fill="url(#portGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Verdeling per belegging</span>
                <PieChart size={15} color="var(--text-muted)" />
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <RPieChart>
                  <Pie data={allocationData} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius={55} outerRadius={90}
                    paddingAngle={2}>
                    {allocationData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                  <Legend iconSize={10} iconType="circle"
                    wrapperStyle={{ fontSize: 11 }} />
                </RPieChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">Verdeling per broker</span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <RPieChart>
                  <Pie data={brokerData} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius={55} outerRadius={90}
                    paddingAngle={2}>
                    {brokerData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                  <Legend iconSize={10} iconType="circle"
                    wrapperStyle={{ fontSize: 11 }} />
                </RPieChart>
              </ResponsiveContainer>
            </div>

            {/* Rendement per belegging */}
            <div className="card" style={{ gridColumn: 'span 2' }}>
              <div className="card-header">
                <span className="card-title">Rendement per belegging (%)</span>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data?.investments ?? []}
                  margin={{ left: 0, right: 0, top: 4, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    tickFormatter={n => n.length > 10 ? n.slice(0, 9) + '…' : n} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
                    tickFormatter={v => `${v}%`} />
                  <Tooltip formatter={(v: number) => `${fmt(v, 2)}%`} />
                  <Bar dataKey="total_return_pct" name="Rendement" radius={[4, 4, 0, 0]}>
                    {(data?.investments ?? []).map((inv, i) => (
                      <Cell
                        key={i}
                        fill={inv.total_return_pct >= 0 ? 'var(--color-gain)' : 'var(--color-loss)'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Beleggingstabel */}
          <div className="card" style={{ marginTop: 0 }}>
            <div className="card-header">
              <span className="card-title">Alle beleggingen</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Naam</th>
                    <th>Ticker</th>
                    <th>Broker</th>
                    <th style={{ textAlign: 'right' }}>Stuks</th>
                    <th style={{ textAlign: 'right' }}>Koers</th>
                    <th style={{ textAlign: 'right' }}>Waarde</th>
                    <th style={{ textAlign: 'right' }}>Rendement</th>
                    <th style={{ textAlign: 'right' }}>%</th>
                    <th style={{ textAlign: 'right' }}>Gewicht</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.investments.map(inv => (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 500 }}>{inv.name}</td>
                      <td className="mono" style={{ color: 'var(--text-secondary)' }}>{inv.ticker ?? '—'}</td>
                      <td>{inv.broker ?? '—'}</td>
                      <td style={{ textAlign: 'right' }} className="mono">{fmt(inv.quantity, 4)}</td>
                      <td style={{ textAlign: 'right' }} className="mono">{fmtCurrency(inv.current_price)}</td>
                      <td style={{ textAlign: 'right' }} className="mono">{fmtCurrency(inv.current_value)}</td>
                      <td style={{ textAlign: 'right' }} className={`mono ${isGain(inv.total_return) ? 'gain' : 'loss'}`}>
                        {fmtCurrency(inv.total_return)}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <span className={`badge ${isGain(inv.total_return_pct) ? 'badge-gain' : 'badge-loss'}`}>
                          {fmtPct(inv.total_return_pct)}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--text-secondary)' }} className="mono">
                        {fmt(inv.weight, 1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="card">
          <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '40px 0' }}>
            Geen beleggingen gevonden. Voeg eerst beleggingen toe in de Portfolio sectie.
          </p>
        </div>
      )}
    </div>
  )
}

// Voeg Receipt import toe
function Receipt(props: any) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width={props.size || 16} height={props.size || 16}
      viewBox="0 0 24 24" fill="none" stroke={props.color || 'currentColor'}
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/>
      <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
      <path d="M12 17.5v-11"/>
    </svg>
  )
}
