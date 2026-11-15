import type { ManageAlertsResult } from '~/types'

/** Ask CheapShark (through Flask) to email a link to manage this email's price alerts */
export function manageAlerts(email: string, signal?: AbortSignal): Promise<ManageAlertsResult> {
  // POST: the email goes in the body, never in a URL
  return apiPost<ManageAlertsResult>('/api/alerts/manage', { email }, signal)
}
