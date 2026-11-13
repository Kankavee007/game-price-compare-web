import type { Currency, Game } from '~/types'

export function searchGames(
  query: string,
  currency: Currency,
  signal?: AbortSignal,
): Promise<Game[]> {
  const params = new URLSearchParams({ query, currency })
  return apiGet<Game[]>(`/api/search?${params}`, signal)
}
