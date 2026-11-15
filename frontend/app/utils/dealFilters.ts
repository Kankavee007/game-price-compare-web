import type { LocationQuery } from 'vue-router'
import { SORT_OPTIONS, type DealFilters, type SortKey } from '~/types'

// The filters live in the URL (/?q=portal&max=300&sort=newest) like the search text, so Back
// from a detail page restores them and a filtered search can be shared as a link.

export function emptyFilters(): DealFilters {
  return { minPrice: null, maxPrice: null, sort: null, stores: [], onSale: false, minRating: null }
}

/** Filters from the route query. Bad values (max=abc, sort=foo) are ignored, as if not set. */
export function filtersFromQuery(query: LocationQuery): DealFilters {
  const text = (key: string) => (typeof query[key] === 'string' ? query[key] : '')
  const sort = text('sort')
  return {
    minPrice: toPrice(text('min')),
    maxPrice: toPrice(text('max')),
    sort: SORT_OPTIONS.some((o) => o.key === sort) ? (sort as SortKey) : null,
    stores: text('stores')
      .split(',')
      .filter((id) => /^\d+$/.test(id)),
    onSale: text('sale') === '1',
    minRating: toRating(text('rating')),
  }
}

/** Route query keys for the filters that are set (unset ones are left out of the URL) */
export function filtersToQuery(f: DealFilters): Record<string, string> {
  return {
    ...(f.minPrice !== null && { min: String(f.minPrice) }),
    ...(f.maxPrice !== null && { max: String(f.maxPrice) }),
    ...(f.sort && { sort: f.sort }),
    ...(f.stores.length && { stores: f.stores.join(',') }),
    ...(f.onSale && { sale: '1' }),
    ...(f.minRating !== null && { rating: String(f.minRating) }),
  }
}

/** How many filters are set; sort counts too, because it changes which games are shown */
export function activeFilterCount(f: DealFilters): number {
  return [
    f.minPrice !== null,
    f.maxPrice !== null,
    f.sort !== null,
    f.stores.length > 0,
    f.onSale,
    f.minRating !== null,
  ].filter(Boolean).length
}

/** Message for an invalid price range, or null when it is fine. The API is not called then. */
export function priceRangeError(f: DealFilters): string | null {
  if ((f.minPrice ?? 0) < 0 || (f.maxPrice ?? 0) < 0) return 'Prices must be 0 or more'
  if (f.minPrice !== null && f.maxPrice !== null && f.minPrice > f.maxPrice) {
    return 'Min price must not be higher than max price'
  }
  return null
}

function toPrice(value: string): number | null {
  if (value === '') return null
  const n = Number(value)
  return Number.isFinite(n) && n >= 0 ? n : null
}

function toRating(value: string): number | null {
  if (!/^\d+$/.test(value)) return null
  const n = Number(value)
  return n <= 100 ? n : null
}
