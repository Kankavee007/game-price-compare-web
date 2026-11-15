<script setup lang="ts">
// listDeals, the filter helpers (utils/) and the components are auto-imported by Nuxt
import { toCurrency, type Currency, type DealFilters, type DealResult } from '~/types'

const DEBOUNCE_MS = 500

// The search and its filters live in the URL (/?q=portal&currency=THB&max=300&sort=newest) so
// the browser Back button from a detail page restores them, and a search can be shared as a link.
const route = useRoute()
const router = useRouter()
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const currency = ref<Currency>(toCurrency(route.query.currency))
const filters = ref<DealFilters>(filtersFromQuery(route.query))
const games = ref<DealResult[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searched = ref<{ query: string; filtered: boolean } | null>(null) // last finished search

// "Load more": page of the last loaded results and how many pages the API has
const page = ref(0)
const totalPages = ref(1)
const loadingMore = ref(false)
const loadMoreError = ref(false)
const hasMore = computed(() => page.value + 1 < totalPages.value)

const hasQuery = computed(() => query.value.trim() !== '')
const filterCount = computed(() => activeFilterCount(filters.value))
const rangeError = computed(() => priceRangeError(filters.value))

let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined
let moreController: AbortController | undefined

async function runSearch() {
  const q = query.value.trim()

  // Cancel the previous request so a slow old response can't overwrite a newer one.
  // A pending "load more" belongs to the old search, so it is cancelled too.
  controller?.abort()
  moreController?.abort()
  loadingMore.value = false
  loadMoreError.value = false

  // An invalid price range shows its message in the filter bar; no request is sent
  if (rangeError.value) {
    loading.value = false
    return
  }

  // Nothing typed and no filter: nothing to show yet
  if (!q && filterCount.value === 0) {
    games.value = []
    error.value = null
    searched.value = null
    loading.value = false
    page.value = 0
    totalPages.value = 1
    return
  }

  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  error.value = null

  try {
    const result = await listDeals(q, currency.value, filters.value, 0, signal)
    games.value = result.results
    page.value = 0
    totalPages.value = result.totalPages
  } catch (err) {
    if (signal.aborted) return
    games.value = []
    totalPages.value = 1
    error.value = err instanceof Error ? err.message : 'Something went wrong'
  }
  loading.value = false
  searched.value = { query: q, filtered: filterCount.value > 0 }
}

async function loadMore() {
  moreController = new AbortController()
  const { signal } = moreController
  loadingMore.value = true
  loadMoreError.value = false

  try {
    const next = page.value + 1
    const result = await listDeals(query.value.trim(), currency.value, filters.value, next, signal)
    // A game can show up on two pages (prices change between requests): show it once
    const shown = new Set(games.value.map((g) => g.gameID))
    games.value = [...games.value, ...result.results.filter((g) => !shown.has(g.gameID))]
    page.value = next
    totalPages.value = result.totalPages
  } catch {
    if (signal.aborted) return
    loadMoreError.value = true
  }
  loadingMore.value = false
}

watch(
  [query, currency, filters],
  () => {
    clearTimeout(timer)
    timer = setTimeout(runSearch, DEBOUNCE_MS)
    // replace, not push: typing should not add a history entry per keystroke
    const q = query.value.trim()
    router.replace({
      query: {
        ...(q && { q }),
        ...(currency.value !== 'USD' && { currency: currency.value }),
        ...filtersToQuery(filters.value),
      },
    })
  },
  { deep: true },
)

// Coming back from a detail page or opening a shared link: search right away
onMounted(() => {
  if (hasQuery.value || filterCount.value > 0) runSearch()
})

// Leaving the page (e.g. to /about) must not leave a timer or request running
onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
  moreController?.abort()
})

// app.vue adds " - Game Price Compare"; an empty title shows the site name only
useHead({ title: () => query.value.trim() })
</script>

<template>
  <div>
    <h1 class="sr-only">Search game prices</h1>

    <div class="flex justify-center">
      <CurrencySelect v-model="currency" />
    </div>

    <hr class="my-6 border-gray-700" />

    <input
      v-model="query"
      type="search"
      placeholder="Search game..."
      aria-label="Search game"
      class="w-full p-3 rounded-xl bg-gray-800 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
    />

    <SearchFilters v-model="filters" :currency="currency" :has-query="hasQuery" />

    <p v-if="loading" class="text-center text-gray-400" role="status">Searching…</p>
    <p v-else-if="error" class="text-center text-red-400" role="alert">⚠️ {{ error }}</p>
    <p v-else-if="searched && games.length === 0" class="text-center text-gray-400">
      <template v-if="searched.query">
        No games found for "{{ searched.query }}"<template v-if="searched.filtered">
          with these filters</template
        >
      </template>
      <template v-else>No games match these filters</template>
    </p>

    <div
      v-if="games.length"
      class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      :class="{ 'opacity-50': loading }"
    >
      <GameCard v-for="game in games" :key="game.gameID" :game="game" />
    </div>

    <div v-if="games.length && !loading && hasMore" class="flex justify-center mt-8">
      <button
        type="button"
        class="px-6 py-3 rounded-xl border focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-60"
        :class="
          loadMoreError
            ? 'border-red-500 text-red-300 hover:bg-red-500/10'
            : 'border-gray-600 bg-gray-800 hover:bg-gray-700'
        "
        :disabled="loadingMore"
        @click="loadMore"
      >
        <template v-if="loadingMore">Loading…</template>
        <template v-else-if="loadMoreError">Failed to load, try again</template>
        <template v-else>Load more</template>
      </button>
    </div>
  </div>
</template>