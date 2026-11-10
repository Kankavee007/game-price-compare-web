import type { Currency, Game } from '@/types'

export async function searchGames(
  query: string,
  currency: Currency,
  signal?: AbortSignal,
): Promise<Game[]> {
  const params = new URLSearchParams({ query, currency })
  const res = await fetch(`/api/search?${params}`, { signal })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.error ?? `Search failed (${res.status})`)
  }
  return res.json()
}
