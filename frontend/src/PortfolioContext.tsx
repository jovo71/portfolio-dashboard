import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { portfoliosApi, Portfolio } from './api'

interface PortfolioCtx {
  portfolios: Portfolio[]
  selectedId: number | null
  setSelectedId: (id: number) => void
  reload: () => Promise<void>
  loading: boolean
}

const Ctx = createContext<PortfolioCtx>({
  portfolios: [], selectedId: null, setSelectedId: () => {}, reload: async () => {}, loading: true,
})

export const usePortfolio = () => useContext(Ctx)

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([])
  const [selectedId, setSelectedIdState] = useState<number | null>(() => {
    const v = localStorage.getItem('portfolioId')
    return v ? Number(v) : null
  })
  const [loading, setLoading] = useState(true)

  function setSelectedId(id: number) {
    setSelectedIdState(id)
    localStorage.setItem('portfolioId', String(id))
  }

  async function reload() {
    try {
      const resp = await portfoliosApi.list()
      setPortfolios(resp.data)
      // Zorg dat de selectie geldig is
      setSelectedIdState(prev => {
        if (resp.data.length === 0) return null
        if (prev != null && resp.data.some(p => p.id === prev)) return prev
        const next = resp.data[0].id
        localStorage.setItem('portfolioId', String(next))
        return next
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, [])

  return (
    <Ctx.Provider value={{ portfolios, selectedId, setSelectedId, reload, loading }}>
      {children}
    </Ctx.Provider>
  )
}
