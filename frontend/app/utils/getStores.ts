import type { Store } from '~/types'

export function getStores(signal?: AbortSignal): Promise<Store[]> {
  return apiGet<Store[]>('/api/stores', signal)
}
