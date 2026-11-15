import type { Genre } from '~/types'

/** IGDB genres sorted by name (GET /api/genres) */
export function getGenres(signal?: AbortSignal): Promise<Genre[]> {
  return apiGet<Genre[]>('/api/genres', signal)
}
