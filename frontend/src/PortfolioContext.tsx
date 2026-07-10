import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { categoriesApi, portfoliosApi, Category, Portfolio } from './api'

interface Ctx {
  categories: Category[]
  /** Portfolio's binnen de geselecteerde categorie. */
  portfolios: Portfolio[]
  /** Alle portfolio's (nodig om ze tussen categorieën te verplaatsen). */
  allPortfolios: Portfolio[]
  selectedCategoryId: number | null
  setSelectedCategoryId: (id: number) => void
  reload: () => Promise<void>
  loading: boolean
}

const Ctx = createContext<Ctx>({
  categories: [], portfolios: [], allPortfolios: [],
  selectedCategoryId: null, setSelectedCategoryId: () => {},
  reload: async () => {}, loading: true,
})

export const usePortfolio = () => useContext(Ctx)

export function PortfolioProvider({ children }: { children: ReactNode }) {
  const [categories, setCategories] = useState<Category[]>([])
  const [allPortfolios, setAllPortfolios] = useState<Portfolio[]>([])
  const [selectedCategoryId, setSelectedIdState] = useState<number | null>(() => {
    const v = localStorage.getItem('categoryId')
    return v ? Number(v) : null
  })
  const [loading, setLoading] = useState(true)

  function setSelectedCategoryId(id: number) {
    setSelectedIdState(id)
    localStorage.setItem('categoryId', String(id))
  }

  async function reload() {
    try {
      const [catResp, pfResp] = await Promise.all([categoriesApi.list(), portfoliosApi.list()])
      setCategories(catResp.data)
      setAllPortfolios(pfResp.data)
      setSelectedIdState(prev => {
        if (catResp.data.length === 0) return null
        if (prev != null && catResp.data.some(c => c.id === prev)) return prev
        const next = catResp.data[0].id
        localStorage.setItem('categoryId', String(next))
        return next
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, [])

  const portfolios = allPortfolios.filter(p => p.category_id === selectedCategoryId)

  return (
    <Ctx.Provider value={{
      categories, portfolios, allPortfolios,
      selectedCategoryId, setSelectedCategoryId, reload, loading,
    }}>
      {children}
    </Ctx.Provider>
  )
}
