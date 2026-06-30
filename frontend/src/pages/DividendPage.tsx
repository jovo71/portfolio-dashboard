import { useState, useEffect } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import toast from 'react-hot-toast'
import { dividendsApi, investmentsApi, Dividend, Investment } from '../api'
import { usePortfolio } from '../PortfolioContext'

function fmtCurrency(v: number) {
  return new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(v)
}

export default function DividendPage() {
  const [dividends, setDividends] = useState<Dividend[]>([])
  const [investments, setInvestments] = useState<Investment[]>([])
  const [summary, setSummary] = useState<{ total: number; by_year: { year: number; total: number }[] } | null>(null)
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    investment_id: '', payment_date: '', amount_per_share: '', total_amount: '', currency: 'EUR',
  })
  const { selectedId } = usePortfolio()

  async function load() {
    if (selectedId == null) return
    setLoading(true)
    try {
      const [divResp, invResp, sumResp] = await Promise.all([
        dividendsApi.list({ portfolioId: selectedId }),
        investmentsApi.list(selectedId),
        dividendsApi.summary(selectedId),
      ])
      setDividends(divResp.data)
      setInvestments(invResp.data)
      setSummary(sumResp.data)
    } catch {
      toast.error('Fout bij laden')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [selectedId])

  async function save() {
    try {
      await dividendsApi.create({
        investment_id: parseInt(form.investment_id),
        payment_date: form.payment_date,
        amount_per_share: parseFloat(form.amount_per_share),
        total_amount: parseFloat(form.total_amount),
        currency: form.currency,
      })
      toast.success('Dividend toegevoegd')
      setShowModal(false)
      load()
    } catch {
      toast.error('Opslaan mislukt')
    }
  }

  async function del(id: number) {
    if (!confirm('Dividend verwijderen?')) return
    try {
      await dividendsApi.delete(id)
      toast.success('Dividend verwijderd')
      load()
    } catch {
      toast.error('Verwijderen mislukt')
    }
  }

  const invMap = Object.fromEntries(investments.map(i => [i.id, i.name]))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1>Dividend</h1>
        <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
          <Plus size={13} /> Dividend toevoegen
        </button>
      </div>

      {/* KPI */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
        <div className="card">
          <div className="card-title">Totaal dividend</div>
          <div className="metric-value gain" style={{ marginTop: 8 }}>
            {fmtCurrency(summary?.total ?? 0)}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Uitbetalingen</div>
          <div className="metric-value" style={{ marginTop: 8 }}>{dividends.length}</div>
        </div>
      </div>

      {/* Grafiek per jaar */}
      {summary?.by_year.length ? (
        <div className="card">
          <div className="card-header"><span className="card-title">Dividend per jaar</span></div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={summary.by_year}>
              <XAxis dataKey="year" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickFormatter={v => `€${v}`} />
              <Tooltip formatter={(v: number) => fmtCurrency(v)} />
              <Bar dataKey="total" name="Dividend" radius={[4, 4, 0, 0]} fill="var(--color-gain)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}

      {/* Tabel */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Belegging</th>
                <th>Datum</th>
                <th style={{ textAlign: 'right' }}>Per aandeel</th>
                <th style={{ textAlign: 'right' }}>Totaal</th>
                <th>Valuta</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40 }}><div className="spinner" style={{ margin: '0 auto' }} /></td></tr>
              ) : dividends.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
                  Nog geen dividend geregistreerd.
                </td></tr>
              ) : dividends.map(d => (
                <tr key={d.id}>
                  <td>{invMap[d.investment_id] ?? `#${d.investment_id}`}</td>
                  <td className="mono">{d.payment_date}</td>
                  <td className="mono" style={{ textAlign: 'right' }}>{fmtCurrency(d.amount_per_share)}</td>
                  <td className="mono gain" style={{ textAlign: 'right' }}>{fmtCurrency(d.total_amount)}</td>
                  <td>{d.currency}</td>
                  <td>
                    <button className="btn btn-danger btn-sm btn-icon" onClick={() => del(d.id)}>
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>Dividend toevoegen</h3>
              <button className="btn btn-secondary btn-sm btn-icon" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Belegging</label>
                <select className="form-control" value={form.investment_id} onChange={e => setForm(f => ({ ...f, investment_id: e.target.value }))}>
                  <option value="">Selecteer belegging</option>
                  {investments.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Uitbetalingsdatum</label>
                <input className="form-control" type="date" value={form.payment_date} onChange={e => setForm(f => ({ ...f, payment_date: e.target.value }))} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Per aandeel (€)</label>
                  <input className="form-control" type="number" step="0.0001" value={form.amount_per_share} onChange={e => setForm(f => ({ ...f, amount_per_share: e.target.value }))} />
                </div>
                <div className="form-group">
                  <label className="form-label">Totaal ontvangen (€)</label>
                  <input className="form-control" type="number" step="0.01" value={form.total_amount} onChange={e => setForm(f => ({ ...f, total_amount: e.target.value }))} />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Annuleren</button>
              <button className="btn btn-primary" onClick={save}>Opslaan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
