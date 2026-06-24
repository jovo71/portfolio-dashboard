// API types en client configuratie
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: API_BASE,
})

// JWT token interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Types
export interface Investment {
  id: number
  name: string
  isin?: string
  ticker?: string
  broker?: string
  quantity: number
  average_purchase_price: number
  currency: string
  purchase_date?: string
  management_fee_percentage: number
  created_at: string
  updated_at?: string
  current_price?: number
  current_value?: number
  total_return?: number
  total_return_pct?: number
  day_change?: number
  day_change_pct?: number
}

export interface PriceHistory {
  id: number
  investment_id: number
  date: string
  price: number
  currency: string
}

export interface Dividend {
  id: number
  investment_id: number
  payment_date: string
  amount_per_share: number
  total_amount: number
  currency: string
  created_at: string
}

export interface CostEntry {
  id: number
  investment_id: number
  cost_type: string
  amount: number
  date: string
  description?: string
  created_at: string
}

export interface PerformanceSummary {
  total_value: number
  total_purchase_value: number
  total_start_value: number
  price_return: number
  price_return_pct: number
  dividend_return: number
  dividend_return_pct: number
  total_costs: number
  total_return: number
  total_return_pct: number
  net_return: number
  net_return_pct: number
  num_investments: number
}

export interface PerformanceData {
  period: string
  period_start?: string
  period_end?: string
  summary: PerformanceSummary
  investments: InvestmentPerformance[]
}

export interface InvestmentPerformance {
  id: number
  name: string
  ticker?: string
  broker?: string
  quantity: number
  current_price: number
  current_value: number
  purchase_value: number
  start_value: number
  price_return: number
  price_return_pct: number
  dividend: number
  costs: number
  total_return: number
  total_return_pct: number
  weight: number
}

export interface SystemStatus {
  scheduler_running: boolean
  last_update?: string
  successful_updates: number
  failed_updates: number
  api_status: string
  last_log?: { timestamp: string; event_type: string; message: string }
  recent_logs: { timestamp: string; event_type: string; message: string }[]
}

// API calls
export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string }>('/auth/login', { username, password }),
}

export const investmentsApi = {
  list: () => api.get<Investment[]>('/investments/'),
  get: (id: number) => api.get<Investment>(`/investments/${id}`),
  create: (data: Partial<Investment>) => api.post<Investment>('/investments/', data),
  update: (id: number, data: Partial<Investment>) => api.put<Investment>(`/investments/${id}`, data),
  delete: (id: number) => api.delete(`/investments/${id}`),
  importCsv: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/investments/import/csv', form)
  },
  exportCsv: () => api.get('/investments/export/csv', { responseType: 'blob' }),
}

export const pricesApi = {
  refresh: () => api.post('/prices/refresh'),
  stats: () => api.get('/prices/stats'),
  history: (investmentId: number) => api.get<PriceHistory[]>(`/prices/${investmentId}/history`),
}

export const dividendsApi = {
  list: (investmentId?: number) =>
    api.get<Dividend[]>('/dividends/', { params: investmentId ? { investment_id: investmentId } : {} }),
  create: (data: Partial<Dividend>) => api.post<Dividend>('/dividends/', data),
  delete: (id: number) => api.delete(`/dividends/${id}`),
  summary: () => api.get('/dividends/summary'),
}

export const costsApi = {
  list: (investmentId?: number) =>
    api.get<CostEntry[]>('/costs/', { params: investmentId ? { investment_id: investmentId } : {} }),
  create: (data: Partial<CostEntry>) => api.post<CostEntry>('/costs/', data),
  delete: (id: number) => api.delete(`/costs/${id}`),
  summary: () => api.get('/costs/summary'),
}

export const performanceApi = {
  get: (period: string, startDate?: string, endDate?: string) =>
    api.get<PerformanceData>('/performance/', {
      params: { period, start_date: startDate, end_date: endDate },
    }),
  history: (days?: number) => api.get<{ date: string; value: number }[]>('/performance/history', { params: { days } }),
}

export interface VersionInfo {
  current_commit: string
  branch: string
  commits_behind: number
  update_available: boolean
  last_commit_message: string
}

export const systemApi = {
  status: () => api.get<SystemStatus>('/system/status'),
  version: () => api.get<VersionInfo>('/system/version'),
  deploy: () => api.post<{ status: string; unit: string }>('/system/deploy'),
}
