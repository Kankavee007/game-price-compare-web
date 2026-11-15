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

const hasQuery = computed(() => query.value.trim() !== '')
const filterCount = computed(() => activeFilterCount(filters.value))
const rangeError = computed(() => priceRangeError(filters.value))

let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined

async function runSearch() {
  const q = query.value.trim()

  // Cancel the previous request so a slow old response can't overwrite a newer one
  controller?.abort()

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
    return
  }

  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  error.value = null

  try {
    games.value = (await listDeals(q, currency.value, filters.value, 0, signal)).results
  } catch (err) {
    if (signal.aborted) return
    games.value = []
    error.value = err instanceof Error ? err.message : 'Something went wrong'
  }
  loading.value = false
  searched.value = { query: q, filtered: filterCount.value > 0 }
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
  </div>
</template>
