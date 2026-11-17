import type { WishlistItem } from '~/types'

const KEY = 'wishlist:v1'
export const WISHLIST_MAX = 50 // GET /api/prices accepts at most 50 ids

function isItem(value: unknown): value is WishlistItem {
  const v = value as WishlistItem
  return (
    typeof v === 'object' &&
    v !== null &&
    typeof v.gameID === 'string' &&
    /^\d+$/.test(v.gameID) &&
    typeof v.name === 'string'
  )
}

// One message for the whole app (shown by the layout), e.g. when storage is blocked
const error = ref<string | null>(null)

/** The wishlist, saved in this browser only (no account), newest first */
export function useWishlist() {
  const { items, save } = storedList(KEY, isItem)

  const has = (gameID: string) => items.value.some((i) => i.gameID === gameID)

  function store(next: WishlistItem[]) {
    error.value = save(next)
      ? null
      : 'Your wishlist cannot be saved in this browser (storage is blocked or full).'
  }

  function add(game: {
    gameID: string
    name: string
    thumb: string | null
    cover?: string | null
  }) {
    if (has(game.gameID)) return
    if (items.value.length >= WISHLIST_MAX) {
      error.value = `Your wishlist is full (${WISHLIST_MAX} games). Remove a game to add another.`
      return
    }
    const item: WishlistItem = {
      gameID: game.gameID,
      name: game.name,
      thumb: game.thumb,
      cover: game.cover ?? null,
      addedAt: new Date().toISOString(),
    }
    store([item, ...items.value])
  }

  function remove(gameID: string) {
    store(items.value.filter((i) => i.gameID !== gameID))
  }

  function toggle(game: {
    gameID: string
    name: string
    thumb: string | null
    cover?: string | null
  }) {
    if (has(game.gameID)) remove(game.gameID)
    else add(game)
  }

  return {
    items: readonly(items),
    count: computed(() => items.value.length),
    has,
    add,
    remove,
    toggle,
    error: readonly(error),
    clearError: () => (error.value = null),
  }
}
