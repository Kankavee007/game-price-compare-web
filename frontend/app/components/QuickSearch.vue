<script setup lang="ts">
// searchGames (utils/) is auto-imported by Nuxt
import { toCurrency, type Game } from '~/types'

// Header search with suggestions. ARIA combobox pattern: focus stays in the input, arrow keys
// move a highlighted option (aria-activedescendant), Enter opens it.

const MAX_SUGGESTIONS = 5
const MIN_LENGTH = 2
const DEBOUNCE_MS = 300

const route = useRoute()
const router = useRouter()
// Prices in the currency the user is browsing in (?currency=THB on the page), else USD
const currency = computed(() => toCurrency(route.query.currency))

const text = ref('')
const open = ref(false) // dropdown shown
const expanded = ref(false) // phone width: the box is folded behind an icon button
const loading = ref(false)
const failed = ref(false)
const results = ref<Game[]>([])
const active = ref(-1) // highlighted option, -1 = none

const input = ref<HTMLInputElement | null>(null)
const ids = { input: useId(), list: useId() }
const optionId = (i: number) => `${ids.list}-${i}`

let controller: AbortController | undefined
let timer: ReturnType<typeof setTimeout> | undefined

function onInput() {
  clearTimeout(timer)
  controller?.abort()
  active.value = -1
  const q = text.value.trim()
  if (q.length < MIN_LENGTH) {
    open.value = false
    loading.value = false
    return
  }
  open.value = true
  loading.value = true
  failed.value = false
  timer = setTimeout(() => fetchSuggestions(q), DEBOUNCE_MS)
}

async function fetchSuggestions(q: string) {
  // Abort the older request so a slow answer for "wit" cannot replace the one for "witcher"
  controller = new AbortController()
  const { signal } = controller
  try {
    results.value = (await searchGames(q, currency.value, signal)).slice(0, MAX_SUGGESTIONS)
    failed.value = false
  } catch {
    if (signal.aborted) return
    results.value = []
    failed.value = true
  }
  loading.value = false
}

function close() {
  open.value = false
  active.value = -1
}

function reset() {
  clearTimeout(timer)
  controller?.abort()
  text.value = ''
  results.value = []
  loading.value = false
  expanded.value = false
  close()
}

function openGame(game: Game) {
  router.push({ path: `/games/${game.gameID}`, query: { currency: currency.value } })
  reset()
  input.value?.blur()
}

/** Enter with nothing highlighted: the full results on the search page */
function goToSearch() {
  const q = text.value.trim()
  if (!q) return
  router.push({
    path: '/',
    query: { q, ...(currency.value !== 'USD' && { currency: currency.value }) },
  })
  reset()
  input.value?.blur()
}

function onKeydown(event: KeyboardEvent) {
  const count = open.value && !loading.value ? results.value.length : 0
  switch (event.key) {
    case 'ArrowDown':
      if (!count) return
      event.preventDefault()
      active.value = (active.value + 1) % count
      break
    case 'ArrowUp':
      if (!count) return
      event.preventDefault()
      active.value = active.value <= 0 ? count - 1 : active.value - 1
      break
    case 'Enter': {
      event.preventDefault()
      const game = active.value >= 0 ? results.value[active.value] : undefined
      if (count && game) openGame(game)
      else goToSearch()
      break
    }
    case 'Escape':
      if (open.value) close()
      else if (expanded.value) reset()
      break
  }
}

// Focus left the whole box (input and dropdown): close. The dropdown options use
// mousedown.prevent, so clicking one does not blur the input first.
function onFocusOut(event: FocusEvent) {
  const box = event.currentTarget as HTMLElement
  if (!box.contains(event.relatedTarget as Node | null)) {
    close()
    if (!text.value.trim()) expanded.value = false
  }
}

async function expand() {
  expanded.value = true
  await nextTick()
  input.value?.focus()
}

// Another page or currency: old suggestions are stale
watch(
  () => route.fullPath,
  () => close(),
)
onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
})

function price(game: Game) {
  return `${game.price.toFixed(2)} ${game.currency}`
}
</script>

<template>
  <div class="relative" @focusout="onFocusOut">
    <!-- Phone width: an icon button until opened -->
    <button
      v-if="!expanded"
      type="button"
      class="sm:hidden p-2 rounded-lg text-gray-300 hover:text-white hover:bg-gray-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      aria-label="Search games"
      @click="expand"
    >
      🔍
    </button>

    <div :class="expanded ? 'block' : 'hidden sm:block'">
      <label :for="ids.input" class="sr-only">Search games</label>
      <input
        :id="ids.input"
        ref="input"
        v-model="text"
        type="search"
        role="combobox"
        autocomplete="off"
        placeholder="Search games…"
        aria-autocomplete="list"
        :aria-expanded="open"
        :aria-controls="ids.list"
        :aria-activedescendant="active >= 0 ? optionId(active) : undefined"
        class="w-44 sm:w-56 p-2 rounded-lg bg-gray-800 border border-gray-700 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        @input="onInput"
        @keydown="onKeydown"
      />
    </div>

    <div
      v-show="open"
      class="absolute right-0 z-20 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-xl bg-gray-800 border border-gray-700 shadow-xl overflow-hidden"
    >
      <p v-if="loading" class="p-3 text-sm text-gray-400" role="status">Searching…</p>
      <p v-else-if="failed" class="p-3 text-sm text-red-300" role="status">
        Suggestions unavailable. Press Enter to search.
      </p>
      <p v-else-if="results.length === 0" class="p-3 text-sm text-gray-400" role="status">
        No games found
      </p>
      <ul :id="ids.list" role="listbox" aria-label="Suggestions" :hidden="loading || failed">
        <li
          v-for="(game, i) in results"
          :id="optionId(i)"
          :key="game.gameID"
          role="option"
          :aria-selected="i === active"
          class="flex items-center gap-3 p-2 cursor-pointer"
          :class="i === active ? 'bg-gray-700' : 'hover:bg-gray-700/60'"
          @mousedown.prevent
          @mousemove="active = i"
          @click="openGame(game)"
        >
          <img
            :src="game.thumb"
            alt=""
            loading="lazy"
            class="w-14 h-7 object-cover rounded shrink-0 bg-gray-700"
          />
          <span class="flex-1 min-w-0 text-sm truncate">{{ game.name }}</span>
          <span class="text-sm text-green-400 font-semibold whitespace-nowrap">{{
            price(game)
          }}</span>
        </li>
      </ul>
      <p v-if="!loading && !failed && results.length" class="px-3 py-2 text-xs text-gray-500">
        Enter: all results for "{{ text.trim() }}"
      </p>
    </div>
  </div>
</template>
