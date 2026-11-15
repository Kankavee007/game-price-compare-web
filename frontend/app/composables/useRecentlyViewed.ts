import type { RecentGame } from '~/types'

const KEY = 'recentlyViewed:v1'
const MAX = 10

function isRecentGame(value: unknown): value is RecentGame {
  const v = value as RecentGame
  return (
    typeof v === 'object' &&
    v !== null &&
    typeof v.gameID === 'string' &&
    /^\d+$/.test(v.gameID) &&
    typeof v.name === 'string'
  )
}

/** Game pages opened in this browser, newest first, at most 10. Nothing is shown on failure. */
export function useRecentlyViewed() {
  const { items, save } = storedList(KEY, isRecentGame)

  /** Put a game at the front (moving it if it was already in the list) */
  function record(game: RecentGame) {
    save([game, ...items.value.filter((g) => g.gameID !== game.gameID)].slice(0, MAX))
  }

  return { items: readonly(items), record, clear: () => save([]) }
}
