/** Lowest price CheapShark has seen for a game (backend/game_api/services/lowest.py) */
export interface LowestPrice {
  lowestPriceEver: number | null // in the response currency
  lowestPriceEverDate: string | null // YYYY-MM-DD
  isHistoricalLow: boolean // today's cheapest price is at (or below) the lowest ever
}

// Response shape of GET /api/search (see backend/game_api/services/search.py)
export interface Game extends LowestPrice {
  gameID: string // CheapShark id, used for /games/<gameID>
  name: string
  price: number
  currency: string
  thumb: string
  storeID: string | null
  storeName: string | null
  dealUrl: string
}

// Response shape of GET /api/games/<id> (see backend/game_api/services/game_detail.py)
export interface Deal {
  storeID: string
  storeName: string | null
  price: number
  retailPrice: number
  savings: number // percent, 0-100
  dealUrl: string
}

export interface GameDetail extends LowestPrice {
  id: string
  name: string
  thumb: string | null
  cover: string | null
  genres: string[]
  rating: number | null // 0-100, IGDB users
  ratingCount: number | null
  criticRating: number | null // 0-100, IGDB critics
  summary: string | null
  releaseDate: string | null // YYYY-MM-DD
  currency: Currency
  deals: Deal[] // cheapest first
}

// Response shape of GET /api/deals (see backend/game_api/services/deals.py)
export interface DealResult extends Game {
  retailPrice: number
  savings: number // percent, 0-100
  steamRating: number | null // percent, null when the game has no Steam reviews
  metacriticScore: number | null
  releaseDate: string | null // YYYY-MM-DD
}

export interface DealPage {
  results: DealResult[] // one per game, its cheapest store
  page: number
  totalPages: number
  currency: Currency
}

// Response shape of GET /api/stores (active stores only, sorted by name)
export interface Store {
  storeID: string
  storeName: string
  logo: string | null
}

export const SORT_OPTIONS = [
  { key: 'relevance', label: 'Best match' }, // only with a search text
  { key: 'deal', label: 'Best deals' },
  { key: 'price', label: 'Price: low to high' },
  { key: 'savings', label: 'Biggest discount' },
  { key: 'reviews', label: 'Steam reviews' },
  { key: 'rating', label: 'Metacritic score' },
  { key: 'newest', label: 'Newest releases' },
] as const

export type SortKey = (typeof SORT_OPTIONS)[number]['key']

/** Filters of the search page; null / empty means "not set". Prices are in the chosen currency. */
export interface DealFilters {
  minPrice: number | null
  maxPrice: number | null
  sort: SortKey | null // null: the API default (relevance with a search text, else best deals)
  stores: string[] // storeIDs
  onSale: boolean
  minRating: number | null // Steam rating percent
}

/** A game saved in the wishlist (localStorage, see composables/useWishlist.ts) */
export interface WishlistItem {
  gameID: string
  name: string
  thumb: string | null
  addedAt: string // ISO date-time
}

// Response shape of GET /api/prices (see backend/game_api/services/prices.py)
export interface GamePrice extends LowestPrice {
  gameID: string
  name: string | null
  thumb: string | null
  price: number
  retailPrice: number
  savings: number // percent, 0-100
  currency: Currency
  storeID: string
  storeName: string | null
  dealUrl: string
}

export const CURRENCIES = [
  { code: 'USD', label: 'USD 💵' },
  { code: 'THB', label: 'THB 🇹🇭' },
  { code: 'EUR', label: 'EUR 💶' },
] as const

export type Currency = (typeof CURRENCIES)[number]['code']

/** A currency code from a URL query value, or USD when it is missing or unknown */
export function toCurrency(value: unknown): Currency {
  return CURRENCIES.some((c) => c.code === value) ? (value as Currency) : 'USD'
}
