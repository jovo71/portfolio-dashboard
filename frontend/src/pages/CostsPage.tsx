import { useState, useEffect } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import toast from 'react-hot-toast'
import { costsApi, investmentsApi, CostEntry, Investment } from '../api'
import { usePortfolio } from '../PortfolioContext'

const COST_TYPES = ['beheerskosten', 'servicekosten', 'transactiekosten', 'bewaarkosten', 'overige kosten']

function fmtCurrency(v: number) {
  return new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(v)
}

export default function CostsPage() {
  const [costs, setCosts] = useState<CostEntry[]>([])
  const [investments, setInvestments] = useState<Investment[]>([])
  const [summary, setSummary] = useState<any>(null)
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    investment_id: '', cost_type: 'beheerskosten', amount: '', date: '', description: '',
  })
  const { selectedCategoryId } = usePortfolio()

  async function load() {
    if (selectedCategoryId == null) return
    setLoading(true)
    try {
      const [costResp, invResp, sumResp] = await Promise.all([
        costsApi.list(selectedCategoryId), investmentsApi.list(selectedCategoryId), costsApi.summary(selectedCategoryId),
      ])
      setCosts(costResp.data)
      setInvestments(invResp.data)
      setSummary(sumResp.data)
    } catch { toast.error('Fout bij laden') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [selectedCategoryId])

  async function save() {
    try {
      await costsApi.create({
        investment_id: parseInt(form.investment_id),
        cost_type: form.cost_type as any,
        amount: parseFloat(form.amount),
        date: form.date,
        description: form.description || undefined,
      })
      toast.success('Kostenpost toegevoegd')
      setShowModal(false)
      load()
    } catch { toast.error('Opslaan mislukt') }
  }

  async function del(id: number) {
    if (!confirm('Kostenpost verwijderen?')) return
    try {
      await costsApi.delete(id)
      toast.success('Verwijderd')
      load()
    } catch { toast.error('Verwijderen mislukt') }
  }

  const invMap = Object.fromEntries(investments.map(i => [i.id, i.name]))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1>Kosten</h1>
        <button className="btn btn-primary btn-sm" onClick={() => setShowModal(true)}>
          <Plus size={13} /> Kostenpost toevoegen
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
        <div className="card">
          <div className="card-title">Kosten dit jaar</div>
          <div className="metric-value" style={{ marginTop: 8, color: 'var(--accent-orange)' }}>
            {fmtCurrency(summary?.this_year ?? 0)}
          </div>
        </div>
        <div className="card">
          <div className="card-title">Totale kosten</div>
          <div className="metric-value" style={{ marginTop: 8, color: 'var(--accent-orange)' }}>
            {fmtCurrency(summary?.total ?? 0)}
          </div>
        </div>
      </div>

      {summary?.by_type?.length ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="card">
            <div className="card-header"><span className="card-title">Kosten per type</span></div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={summary.by_type} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickFormatter={v => `€${v}`} />
                <YAxis type="category" dataKey="type" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} width={100}
                  tickFormatter={v => v.replace('kosten', '')} />
                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                <Bar dataKey="total" name="Kosten" fill="var(--accent-orange)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title">Kosten per broker</span></div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={summary.by_broker}>
                <XAxis dataKey="broker" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickFormatter={v => `€${v}`} />
                <Tooltip formatter={(v: number) => fmtCurrency(v)} />
                <Bar dataKey="total" name="Kosten" fill="var(--accent-orange)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : null}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Belegging</th>
                <th>Type</th>
                <th>Omschrijving</th>
                <th>Datum</th>
                <th style={{ textAlign: 'right' }}>Bedrag</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40 }}><div className="spinner" style={{ margin: '0 auto' }} /></td></tr>
              ) : costs.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
                  Nog geen kosten geregistreerd.
                </td></tr>
              ) : costs.map(c => (
                <tr key={c.id}>
                  <td>{invMap[c.investment_id] ?? `#${c.investment_id}`}</td>
                  <td><span style={{ fontSize: 12, color: 'var(--accent-orange)' }}>{c.cost_type}</span></td>
                  <td style={{ color: 'var(--text-secondary)' }}>{c.description ?? '—'}</td>
                  <td className="mono">{c.date}</td>
                  <td className="mono" style={{ textAlign: 'right', color: 'var(--accent-orange)' }}>{fmtCurrency(c.amount)}</td>
                  <td>
                    <button className="btn btn-danger btn-sm btn-icon" onClick={() => del(c.id)}>
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
              <h3>Kostenpost toevoegen</h3>
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
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Type</label>
                  <select className="form-control" value={form.cost_type} onChange={e => setForm(f => ({ ...f, cost_type: e.target.value }))}>
                    {COST_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Bedrag (€)</label>
                  <input className="form-control" type="number" step="0.01" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Datum</label>
                <input className="form-control" type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Omschrijving</label>
                <input className="form-control" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="optioneel" />
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
