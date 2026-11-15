import type { Currency, PriceAlertResult } from '~/types'

/** Ask CheapShark (through Flask) to email `email` when the game drops below `price` */
export function setPriceAlert(
  alert: { email: string; gameID: string; price: number; currency: Currency },
  signal?: AbortSignal,
): Promise<PriceAlertResult> {
  // POST: the email goes in the body, never in a URL
  return apiPost<PriceAlertResult>('/api/alerts', alert, signal)
}
