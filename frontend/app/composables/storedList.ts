// A list kept in localStorage and shared by every component that uses the same key.
// Used by useWishlist and useRecentlyViewed.
//
// localStorage can throw (blocked site data, some private modes) or be full, and its content can
// be broken JSON (edited by hand, an old format). Every read and write is wrapped, so the page
// never crashes: a failed read gives an empty list, a failed write keeps the list as it was and
// reports `false` so the caller can show a message.

interface StoredList<T> {
  items: Ref<T[]>
  /** Save a new list. Returns false (and keeps the old list) when storage refuses it. */
  save: (next: T[]) => boolean
}

const lists = new Map<string, StoredList<unknown>>()

export function storedList<T>(key: string, isValid: (item: unknown) => item is T): StoredList<T> {
  const existing = lists.get(key)
  if (existing) return existing as StoredList<T>

  const items = ref<T[]>([]) as Ref<T[]>

  function read(): T[] {
    try {
      const raw = window.localStorage.getItem(key)
      const data: unknown = raw ? JSON.parse(raw) : []
      return Array.isArray(data) ? data.filter(isValid) : []
    } catch {
      return []
    }
  }

  function save(next: T[]): boolean {
    try {
      window.localStorage.setItem(key, JSON.stringify(next))
    } catch {
      return false
    }
    items.value = next
    return true
  }

  // Only in the browser: prerendering /about runs this on the server, where there is no storage
  if (import.meta.client) {
    items.value = read()
    // Another tab changed the list (key null: that tab cleared all storage)
    window.addEventListener('storage', (event) => {
      if (event.key === key || event.key === null) items.value = read()
    })
  }

  const list: StoredList<T> = { items, save }
  lists.set(key, list as StoredList<unknown>)
  return list
}
