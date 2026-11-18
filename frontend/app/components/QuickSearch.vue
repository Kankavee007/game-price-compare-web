<script setup lang="ts">
// searchGames (utils/) is auto-imported by Nuxt
import { toCurrency, type Game } from '~/types'

// Header search with suggestions. ARIA combobox pattern: focus stays in the input, arrow keys
// move a highlighted option (aria-activedescendant), Enter opens it.

// iconUntilLg: the box stays folded behind the icon button up to lg (not just sm), so showing
// it on / never makes the top bar wrap to a taller second row while the user scrolls
const props = defineProps<{ iconUntilLg?: boolean }>()

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
      class="grid place-items-center w-9 h-9 rounded-xl text-fg/80 hover:text-fg hover:bg-surface-2/70 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      aria-label="Search games"
      :class="props.iconUntilLg ? 'lg:hidden' : 'sm:hidden'"
      @click="expand"
    >
      🔍
    </button>

    <div :class="expanded ? 'block' : props.iconUntilLg ? 'hidden lg:block' : 'hidden sm:block'">
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
        class="field w-44 sm:w-56 lg:w-64 xl:w-96 p-2 text-sm"
        @input="onInput"
        @keydown="onKeydown"
      />
    </div>

    <div
      v-show="open"
      class="absolute right-0 lg:right-auto lg:left-1/2 lg:-translate-x-1/2 z-20 mt-2 w-80 lg:w-96 max-w-[calc(100vw-2rem)] rounded-2xl bg-surface/95 backdrop-blur border border-line shadow-2xl shadow-black/40 overflow-hidden"
    >
      <p v-if="loading" class="p-3 text-sm text-muted" role="status">Searching…</p>
      <p v-else-if="failed" class="p-3 text-sm text-danger" role="status">
        Suggestions unavailable. Press Enter to search.
      </p>
      <p v-else-if="results.length === 0" class="p-3 text-sm text-muted" role="status">
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
          :class="i === active ? 'bg-surface-2' : 'hover:bg-surface-2/60'"
          @mousedown.prevent
          @mousemove="active = i"
          @click="openGame(game)"
        >
          <img
            :src="game.thumb"
            alt=""
            loading="lazy"
            class="w-14 h-7 object-cover rounded shrink-0 bg-surface-2"
          />
          <span class="flex-1 min-w-0 text-sm truncate">{{ game.name }}</span>
          <span class="text-sm text-success font-semibold whitespace-nowrap">{{
            price(game)
          }}</span>
        </li>
      </ul>
      <p v-if="!loading && !failed && results.length" class="px-3 py-2 text-xs text-subtle">
        Enter: all results for "{{ text.trim() }}"
      </p>
    </div>
  </div>
</template>
