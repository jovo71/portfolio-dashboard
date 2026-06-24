import { useState, useEffect, useRef } from 'react'
import { Plus, Edit2, Trash2, Upload, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import { investmentsApi, Investment } from '../api'
import styles from './PortfolioPage.module.css'

const BROKERS = ['DeGiro', 'Rabobank', 'Andere']
const CURRENCIES = ['EUR', 'USD', 'GBP', 'CHF']

type FormData = {
  name: string; ticker: string; broker: string
  quantity: string; average_purchase_price: string; currency: string
  purchase_date: string; management_fee_percentage: string
}

const EMPTY_FORM: FormData = {
  name: '', ticker: '', broker: 'DeGiro',
  quantity: '', average_purchase_price: '', currency: 'EUR',
  purchase_date: '', management_fee_percentage: '0',
}

function fmtCurrency(v?: number) {
  if (v == null) return '—'
  return new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(v)
}

export default function PortfolioPage() {
  const [investments, setInvestments] = useState<Investment[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<Investment | null>(null)
  const [form, setForm] = useState<FormData>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  async function load() {
    setLoading(true)
    try {
      const resp = await investmentsApi.list()
      setInvestments(resp.data)
    } catch {
      toast.error('Fout bij laden van beleggingen')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function openNew() {
    setEditing(null)
    setForm(EMPTY_FORM)
    setShowModal(true)
  }

  function openEdit(inv: Investment) {
    setEditing(inv)
    setForm({
      name: inv.name,
      ticker: inv.ticker ?? '',
      broker: inv.broker ?? 'DeGiro',
      quantity: String(inv.quantity),
      average_purchase_price: String(inv.average_purchase_price),
      currency: inv.currency,
      purchase_date: inv.purchase_date ?? '',
      management_fee_percentage: String(inv.management_fee_percentage),
    })
    setShowModal(true)
  }

  async function save() {
    if (!form.name || !form.quantity || !form.average_purchase_price) {
      toast.error('Vul alle verplichte velden in')
      return
    }
    setSaving(true)
    try {
      const payload = {
        name: form.name,
        ticker: form.ticker || undefined,
        broker: form.broker || undefined,
        quantity: parseFloat(form.quantity),
        average_purchase_price: parseFloat(form.average_purchase_price),
        currency: form.currency,
        purchase_date: form.purchase_date || undefined,
        management_fee_percentage: parseFloat(form.management_fee_percentage) || 0,
      }
      if (editing) {
        await investmentsApi.update(editing.id, payload)
        toast.success('Belegging bijgewerkt')
      } else {
        await investmentsApi.create(payload)
        toast.success('Belegging toegevoegd')
      }
      setShowModal(false)
      load()
    } catch {
      toast.error('Opslaan mislukt')
    } finally {
      setSaving(false)
    }
  }

  async function del(inv: Investment) {
    if (!confirm(`Weet u zeker dat u "${inv.name}" wilt verwijderen?`)) return
    try {
      await investmentsApi.delete(inv.id)
      toast.success('Belegging verwijderd')
      load()
    } catch {
      toast.error('Verwijderen mislukt')
    }
  }

  async function importCsv(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const resp = await investmentsApi.importCsv(file)
      toast.success(`${resp.data.imported} beleggingen geïmporteerd`)
      if (resp.data.errors?.length) {
        toast.error(`${resp.data.errors.length} fouten bij import`)
      }
      load()
    } catch {
      toast.error('CSV import mislukt')
    }
  }

  async function exportCsv() {
    try {
      const resp = await investmentsApi.exportCsv()
      const url = URL.createObjectURL(new Blob([resp.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = 'beleggingen.csv'
      a.click()
    } catch {
      toast.error('Export mislukt')
    }
  }

  const setField = (k: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Portfolio</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <input ref={fileRef} type="file" accept=".csv" onChange={importCsv} style={{ display: 'none' }} />
          <button className="btn btn-secondary btn-sm" onClick={() => fileRef.current?.click()}>
            <Upload size={13} /> CSV importeren
          </button>
          <button className="btn btn-secondary btn-sm" onClick={exportCsv}>
            <Download size={13} /> Exporteren
          </button>
          <button className="btn btn-primary btn-sm" onClick={openNew}>
            <Plus size={13} /> Belegging toevoegen
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /> Laden…</div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Naam</th>
                  <th>Ticker</th>
                  <th>Broker</th>
                  <th style={{ textAlign: 'right' }}>Stuks</th>
                  <th style={{ textAlign: 'right' }}>Aankoopprijs</th>
                  <th style={{ textAlign: 'right' }}>Koers</th>
                  <th style={{ textAlign: 'right' }}>Waarde</th>
                  <th style={{ textAlign: 'right' }}>Vandaag</th>
                  <th style={{ textAlign: 'right' }}>Totaal</th>
                  <th>Acties</th>
                </tr>
              </thead>
              <tbody>
                {investments.length === 0 ? (
                  <tr><td colSpan={10} style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
                    Nog geen beleggingen. Klik op "Belegging toevoegen" om te beginnen.
                  </td></tr>
                ) : investments.map(inv => {
                  const isGain = (inv.total_return_pct ?? 0) >= 0
                  const dayGain = (inv.day_change_pct ?? 0) >= 0
                  return (
                    <tr key={inv.id}>
                      <td style={{ fontWeight: 500 }}>{inv.name}</td>
                      <td className="mono">{inv.ticker ?? '—'}</td>
                      <td>
                        <span className={`${styles.brokerBadge} ${inv.broker === 'DeGiro' ? styles.degiro : styles.rabobank}`}>
                          {inv.broker ?? '—'}
                        </span>
                      </td>
                      <td className="mono" style={{ textAlign: 'right' }}>{inv.quantity}</td>
                      <td className="mono" style={{ textAlign: 'right' }}>{fmtCurrency(inv.average_purchase_price)}</td>
                      <td className="mono" style={{ textAlign: 'right' }}>{fmtCurrency(inv.current_price)}</td>
                      <td className="mono" style={{ textAlign: 'right' }}>{fmtCurrency(inv.current_value)}</td>
                      <td style={{ textAlign: 'right' }}>
                        {inv.day_change_pct != null ? (
                          <span className={`badge ${dayGain ? 'badge-gain' : 'badge-loss'}`}>
                            {dayGain ? '+' : ''}{inv.day_change_pct.toFixed(2)}%
                          </span>
                        ) : '—'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {inv.total_return_pct != null ? (
                          <span className={`badge ${isGain ? 'badge-gain' : 'badge-loss'}`}>
                            {isGain ? '+' : ''}{inv.total_return_pct.toFixed(2)}%
                          </span>
                        ) : '—'}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className="btn btn-secondary btn-sm btn-icon" onClick={() => openEdit(inv)}>
                            <Edit2 size={12} />
                          </button>
                          <button className="btn btn-danger btn-sm btn-icon" onClick={() => del(inv)}>
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowModal(false)}>
          <div className="modal">
            <div className="modal-header">
              <h3>{editing ? 'Belegging bewerken' : 'Belegging toevoegen'}</h3>
              <button className="btn btn-secondary btn-sm btn-icon" onClick={() => setShowModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label className="form-label">Naam *</label>
                  <input className="form-control" value={form.name} onChange={setField('name')} placeholder="bijv. VWRL ETF" />
                </div>
                <div className="form-group">
                  <label className="form-label">Ticker</label>
                  <input className="form-control" value={form.ticker} onChange={setField('ticker')} placeholder="VWRL.AS" />
                </div>
                <div className="form-group">
                  <label className="form-label">Broker</label>
                  <select className="form-control" value={form.broker} onChange={setField('broker')}>
                    {BROKERS.map(b => <option key={b}>{b}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Valuta</label>
                  <select className="form-control" value={form.currency} onChange={setField('currency')}>
                    {CURRENCIES.map(c => <option key={c}>{c}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Aantal stuks *</label>
                  <input className="form-control" type="number" step="0.0001" value={form.quantity} onChange={setField('quantity')} placeholder="10" />
                </div>
                <div className="form-group">
                  <label className="form-label">Gem. aankoopprijs (€) *</label>
                  <input className="form-control" type="number" step="0.01" value={form.average_purchase_price} onChange={setField('average_purchase_price')} placeholder="100.00" />
                </div>
                <div className="form-group">
                  <label className="form-label">Aankoopdatum</label>
                  <input className="form-control" type="date" value={form.purchase_date} onChange={setField('purchase_date')} />
                </div>
                <div className="form-group">
                  <label className="form-label">Beheerskosten (%/jaar)</label>
                  <input className="form-control" type="number" step="0.01" value={form.management_fee_percentage} onChange={setField('management_fee_percentage')} placeholder="0.22" />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Annuleren</button>
              <button className="btn btn-primary" onClick={save} disabled={saving}>
                {saving ? 'Opslaan…' : 'Opslaan'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
