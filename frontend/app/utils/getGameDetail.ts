import type { Currency, GameDetail } from '~/types'

export function getGameDetail(
  id: string,
  currency: Currency,
  signal?: AbortSignal,
): Promise<GameDetail> {
  const params = new URLSearchParams({ currency })
  return apiGet<GameDetail>(`/api/games/${encodeURIComponent(id)}?${params}`, signal)
}
