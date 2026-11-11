import type { Currency, Game } from '~/types'

// Give up instead of showing "Searching…" forever. The backend makes up to 4 upstream calls
// with a 10 s timeout each, and the Nuxt dev proxy never answers when Flask is not running.
const TIMEOUT_MS = 30_000

export async function searchGames(
  query: string,
  currency: Currency,
  signal?: AbortSignal,
): Promise<Game[]> {
  const params = new URLSearchParams({ query, currency })
  const timeout = AbortSignal.timeout(TIMEOUT_MS)
  // Abort on whichever comes first: the caller cancels (newer search) or the timeout
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout

  let res: Response
  try {
    res = await fetch(`/api/search?${params}`, { signal: combined })
  } catch (err) {
    if (timeout.aborted && !signal?.aborted) {
      throw new Error('The server took too long to respond. Please try again.')
    }
    throw err
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.error ?? `Search failed (${res.status})`)
  }
  return res.json()
}
