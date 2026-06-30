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
export interface Portfolio {
  id: number
  name: string
  created_at: string
  num_investments: number
}

export interface Investment {
  id: number
  portfolio_id?: number
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
  price_updated_at?: string
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

export const portfoliosApi = {
  list: () => api.get<Portfolio[]>('/portfolios/'),
  create: (name: string) => api.post<Portfolio>('/portfolios/', { name }),
  rename: (id: number, name: string) => api.put<Portfolio>(`/portfolios/${id}`, { name }),
  delete: (id: number) => api.delete(`/portfolios/${id}`),
}

export const investmentsApi = {
  list: (portfolioId?: number) =>
    api.get<Investment[]>('/investments/', { params: portfolioId ? { portfolio_id: portfolioId } : {} }),
  get: (id: number) => api.get<Investment>(`/investments/${id}`),
  create: (data: Partial<Investment>) => api.post<Investment>('/investments/', data),
  update: (id: number, data: Partial<Investment>) => api.put<Investment>(`/investments/${id}`, data),
  delete: (id: number) => api.delete(`/investments/${id}`),
  importCsv: (file: File, portfolioId?: number) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/investments/import/csv', form, { params: portfolioId ? { portfolio_id: portfolioId } : {} })
  },
  exportCsv: (portfolioId?: number) =>
    api.get('/investments/export/csv', { responseType: 'blob', params: portfolioId ? { portfolio_id: portfolioId } : {} }),
}

export const pricesApi = {
  refresh: () => api.post('/prices/refresh'),
  stats: () => api.get('/prices/stats'),
  history: (investmentId: number) => api.get<PriceHistory[]>(`/prices/${investmentId}/history`),
  backfill: (investmentId: number, period = '1y') =>
    api.post<{ added: number; reason?: string }>(`/prices/${investmentId}/backfill`, null, { params: { period } }),
}

export const dividendsApi = {
  list: (opts?: { investmentId?: number; portfolioId?: number }) =>
    api.get<Dividend[]>('/dividends/', {
      params: {
        ...(opts?.investmentId ? { investment_id: opts.investmentId } : {}),
        ...(opts?.portfolioId ? { portfolio_id: opts.portfolioId } : {}),
      },
    }),
  create: (data: Partial<Dividend>) => api.post<Dividend>('/dividends/', data),
  delete: (id: number) => api.delete(`/dividends/${id}`),
  summary: (portfolioId?: number) =>
    api.get('/dividends/summary', { params: portfolioId ? { portfolio_id: portfolioId } : {} }),
}

export const costsApi = {
  list: (opts?: { investmentId?: number; portfolioId?: number }) =>
    api.get<CostEntry[]>('/costs/', {
      params: {
        ...(opts?.investmentId ? { investment_id: opts.investmentId } : {}),
        ...(opts?.portfolioId ? { portfolio_id: opts.portfolioId } : {}),
      },
    }),
  create: (data: Partial<CostEntry>) => api.post<CostEntry>('/costs/', data),
  delete: (id: number) => api.delete(`/costs/${id}`),
  summary: (portfolioId?: number) =>
    api.get('/costs/summary', { params: portfolioId ? { portfolio_id: portfolioId } : {} }),
}

export const performanceApi = {
  get: (period: string, startDate?: string, endDate?: string, portfolioId?: number) =>
    api.get<PerformanceData>('/performance/', {
      params: { period, start_date: startDate, end_date: endDate, ...(portfolioId ? { portfolio_id: portfolioId } : {}) },
    }),
  history: (days?: number, portfolioId?: number) =>
    api.get<{ date: string; value: number }[]>('/performance/history', {
      params: { days, ...(portfolioId ? { portfolio_id: portfolioId } : {}) },
    }),
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
