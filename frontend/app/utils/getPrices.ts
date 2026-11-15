import type { Currency, GamePrice } from '~/types'

/** Current cheapest deal of up to 50 games; unknown games are left out of the result */
export function getPrices(
  gameIDs: readonly string[],
  currency: Currency,
  signal?: AbortSignal,
): Promise<GamePrice[]> {
  const params = new URLSearchParams({ ids: gameIDs.join(','), currency })
  return apiGet<GamePrice[]>(`/api/prices?${params}`, signal)
}
