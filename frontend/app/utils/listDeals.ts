import type { Currency, DealFilters, DealPage } from '~/types'

export function listDeals(
  query: string,
  currency: Currency,
  filters: DealFilters,
  page = 0,
  signal?: AbortSignal,
): Promise<DealPage> {
  const params = new URLSearchParams({ currency })
  if (query) params.set('q', query)
  if (filters.minPrice !== null) params.set('minPrice', String(filters.minPrice))
  if (filters.maxPrice !== null) params.set('maxPrice', String(filters.maxPrice))
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.stores.length) params.set('stores', filters.stores.join(','))
  if (filters.onSale) params.set('onSale', '1')
  if (filters.minRating !== null) params.set('minRating', String(filters.minRating))
  if (page > 0) params.set('page', String(page))
  return apiGet<DealPage>(`/api/deals?${params}`, signal)
}
