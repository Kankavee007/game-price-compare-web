// Give up instead of showing "Loading…" forever. The backend makes several upstream calls
// with a 10 s timeout each, and the Nuxt dev proxy never answers when Flask is not running.
const TIMEOUT_MS = 30_000

/** Error from /api with the HTTP status, so pages can tell "not found" (404) apart from "down" */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

/** GET a /api URL and return its JSON. Throws ApiError on a non-2xx answer or a timeout. */
export async function apiGet<T>(url: string, signal?: AbortSignal): Promise<T> {
  const timeout = AbortSignal.timeout(TIMEOUT_MS)
  // Abort on whichever comes first: the caller cancels (newer request) or the timeout
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout

  let res: Response
  try {
    res = await fetch(url, { signal: combined })
  } catch (err) {
    if (timeout.aborted && !signal?.aborted) {
      throw new ApiError('The server took too long to respond. Please try again.', 0)
    }
    throw err
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(body?.error ?? `Request failed (${res.status})`, res.status)
  }
  return res.json()
}
