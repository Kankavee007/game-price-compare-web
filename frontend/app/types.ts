// Response shape of GET /api/search (see backend/game_api/services/search.py)
export interface Game {
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

export interface GameDetail {
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
