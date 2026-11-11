// Response shape of GET /api/search (see backend/game_api/services/search.py)
export interface Game {
  name: string
  price: number
  currency: string
  thumb: string
  storeID: string | null
  storeName: string | null
  dealUrl: string
}

export const CURRENCIES = [
  { code: 'USD', label: 'USD 💵' },
  { code: 'THB', label: 'THB 🇹🇭' },
  { code: 'EUR', label: 'EUR 💶' },
] as const

export type Currency = (typeof CURRENCIES)[number]['code']
