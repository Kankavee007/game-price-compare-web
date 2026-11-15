import type { BrowseResult, Currency } from '~/types'

/** Popular PC games of a genre with the cheapest price (GET /api/browse) */
export function browseGenre(
  genre: string,
  currency: Currency,
  signal?: AbortSignal,
): Promise<BrowseResult> {
  const params = new URLSearchParams({ genre, currency })
  return apiGet<BrowseResult>(`/api/browse?${params}`, signal)
}
