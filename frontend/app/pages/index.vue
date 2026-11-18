<script setup lang="ts">
// listDeals, the filter helpers (utils/) and the components are auto-imported by Nuxt
import {
  toCurrency,
  type Currency,
  type DealFilters,
  type DealPage,
  type DealResult,
} from '~/types'

const DEBOUNCE_MS = 500
// A link with ?page=N loads pages 0..N at once; capped so a link cannot trigger hundreds of requests
const MAX_RESTORE_PAGE = 20
// Restored pages load this many at a time: 21 at once overwhelmed the dev proxy (503s)
// and would hit CheapShark's rate limit
const RESTORE_CONCURRENCY = 4

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

// ?page=N in the URL: the last "Load more" page. Back from a detail page loads them all again.
function toPageNumber(value: unknown): number {
  if (typeof value !== 'string' || !/^\d+$/.test(value)) return 0
  return Math.min(Number(value), MAX_RESTORE_PAGE)
}

const hasQuery = computed(() => query.value.trim() !== '')
// Nothing typed and no filter: show the landing sections instead of results
const showLanding = computed(() => !hasQuery.value && filterCount.value === 0)

// Landing sections. "Top rated" sorts by Metacritic score; "New releases" needs on sale +
// Steam 80%+, else page 0 is all future placeholder dates (checked live 2026-11-15).
const TOP_RATED: Partial<DealFilters> = { sort: 'rating', onSale: true }
const NEW_RELEASES: Partial<DealFilters> = { sort: 'newest', minRating: 80, onSale: true }
const FREE_NOW: Partial<DealFilters> = { maxPrice: 0, onSale: true }
const filterCount = computed(() => activeFilterCount(filters.value))
const rangeError = computed(() => priceRangeError(filters.value))

let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined
let moreController: AbortController | undefined

async function runSearch(upTo = 0) {
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
    // Pages 0..upTo (upTo > 0 only when restoring a URL with ?page=N)
    const pages = await loadPages(q, upTo, signal)
    games.value = withoutDuplicates(pages.flatMap((r) => r.results))
    totalPages.value = pages[0]!.totalPages
    // A page past the end (old link, fewer deals now) counts as the last page
    page.value = Math.min(upTo, totalPages.value - 1)
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
    games.value = withoutDuplicates([...games.value, ...result.results])
    page.value = next
    totalPages.value = result.totalPages
    router.replace({ query: { ...route.query, page: String(next) } })
  } catch {
    if (signal.aborted) return
    loadMoreError.value = true
  }
  loadingMore.value = false
}

/** The URL query for a search (without page) */
function searchQuery(q: string, cur: Currency, f: DealFilters): Record<string, string> {
  return {
    ...(q && { q }),
    ...(cur !== 'USD' && { currency: cur }),
    ...filtersToQuery(f),
  }
}

watch(
  [query, currency, filters],
  () => {
    clearTimeout(timer)
    timer = setTimeout(runSearch, DEBOUNCE_MS)
    // replace, not push: typing should not add a history entry per keystroke
    router.replace({ query: searchQuery(query.value.trim(), currency.value, filters.value) })
  },
  { deep: true },
)

// The URL changed from outside this page (a "See all" link, the header "Search" link): load
// that search. Our own router.replace calls give the same search back, so they are skipped.
// Both sides are parsed first, so bad values left in the URL (max=abc) do not count as a change.
watch(
  () => route.query,
  (rq) => {
    const q = typeof rq.q === 'string' ? rq.q : ''
    const incoming = searchQuery(q.trim(), toCurrency(rq.currency), filtersFromQuery(rq))
    const current = searchQuery(query.value.trim(), currency.value, filters.value)
    if (JSON.stringify(incoming) === JSON.stringify(current)) return
    query.value = q
    currency.value = toCurrency(rq.currency)
    filters.value = filtersFromQuery(rq)
    window.scrollTo({ top: 0 })
  },
)

/** Pages 0..upTo, RESTORE_CONCURRENCY requests at a time, returned in page order */
async function loadPages(q: string, upTo: number, signal: AbortSignal): Promise<DealPage[]> {
  const pages: DealPage[] = []
  let next = 0
  async function worker() {
    while (next <= upTo) {
      const p = next++
      pages[p] = await listDeals(q, currency.value, filters.value, p, signal)
    }
  }
  await Promise.all(Array.from({ length: Math.min(RESTORE_CONCURRENCY, upTo + 1) }, worker))
  return pages
}

// A game can show up on two pages (prices change between requests): show it once
function withoutDuplicates(list: DealResult[]): DealResult[] {
  const seen = new Set<string>()
  return list.filter((g) => !seen.has(g.gameID) && seen.add(g.gameID))
}

// Coming back from a detail page or opening a shared link: search right away.
// Vue Router saves the scroll position in history.state when leaving a page. Its own scroll
// restore runs before the results arrive (the page is still short), so scroll again after them.
onMounted(async () => {
  if (!hasQuery.value && filterCount.value === 0) return
  const saved = window.history.state?.scroll as { top?: number } | undefined
  await runSearch(toPageNumber(route.query.page))
  if (saved?.top) {
    await nextTick()
    window.scrollTo({ top: saved.top })
  }
})

// Leaving the page (e.g. to /about) must not leave a timer or request running
onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
  moreController?.abort()
})

// The top bar shows its own search box on / once this page's box is out of view
const searchBox = ref<HTMLInputElement | null>(null)
const pageSearchVisible = usePageSearchVisible()
let searchObserver: IntersectionObserver | undefined

onMounted(() => {
  if (!('IntersectionObserver' in window) || !searchBox.value) {
    pageSearchVisible.value = false // no observer: the top bar box is simply always shown
    return
  }
  // The sticky top bar covers the top of the screen; a box under it counts as out of view
  const barHeight = document.querySelector('header')?.offsetHeight ?? 0
  searchObserver = new IntersectionObserver(
    ([entry]) => {
      pageSearchVisible.value = !!entry?.isIntersecting
    },
    { rootMargin: `-${barHeight}px 0px 0px 0px` },
  )
  searchObserver.observe(searchBox.value)
})

onBeforeUnmount(() => {
  searchObserver?.disconnect()
  pageSearchVisible.value = true
})

// Hero arrow: scroll to the filters and deals, and move focus there for keyboard users
const content = ref<HTMLElement | null>(null)
function scrollToContent() {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  content.value?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  content.value?.focus({ preventScroll: true })
}

// app.vue adds " - PixSales"; an empty title shows "PixSales - Pixel Perfect Deals"
useHead({ title: () => query.value.trim() })
</script>

<template>
  <div>
    <h1 class="sr-only">PixSales: search game prices</h1>

    <!-- Landing view: a hero that fills the first screen (logo, search box, down arrow).
         Once a search or filter is set it shrinks to just the search box across the full width.
         It is one input in both states, so typing never loses focus. -->
    <section
      class="relative flex flex-col items-center justify-center transition-[min-height] duration-300 ease-out motion-reduce:transition-none"
      :class="showLanding ? 'hero-screen pb-20' : 'min-h-0'"
    >
      <Transition
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 max-h-0"
        enter-to-class="opacity-100 max-h-60"
        leave-active-class="transition-all duration-200 ease-in overflow-hidden"
        leave-from-class="opacity-100 max-h-60"
        leave-to-class="opacity-0 max-h-0"
      >
        <BrandLogo v-if="showLanding" class="w-full pb-8" />
      </Transition>

      <input
        ref="searchBox"
        v-model="query"
        type="search"
        placeholder="Search game..."
        aria-label="Search game"
        class="field w-full px-4 py-3 text-lg rounded-2xl shadow-lg shadow-black/20 transition-[max-width] duration-300 motion-reduce:transition-none"
        :class="showLanding ? 'max-w-2xl' : 'max-w-full'"
      />

      <Transition
        enter-active-class="transition-opacity duration-300"
        enter-from-class="opacity-0"
        leave-active-class="transition-opacity duration-150"
        leave-to-class="opacity-0"
      >
        <div v-if="showLanding" class="absolute inset-x-0 bottom-2 flex justify-center">
          <button
            type="button"
            aria-label="Scroll to deals"
            class="hint-bounce grid place-items-center w-11 h-11 rounded-full border border-line bg-surface/70 text-muted hover:text-fg hover:border-line-strong transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            @click="scrollToContent"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              class="w-5 h-5"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
        </div>
      </Transition>
    </section>

    <!-- lg: filters | results (discounts below the results). xl: filters | results | discounts.
         Below lg: one column, filters above the results. -->
    <div
      ref="content"
      tabindex="-1"
      class="mt-6 scroll-mt-32 sm:scroll-mt-24 focus:outline-none lg:grid lg:grid-cols-[15rem_minmax(0,1fr)] xl:grid-cols-[15rem_minmax(0,1fr)_16rem] lg:gap-8"
    >
      <!-- Pinned under the top bar, but only on screens tall enough to show the whole column.
           relative z-10: its dropdowns open over the result cards. -->
      <aside v-reveal class="relative z-10 lg:self-start lg:top-24 lg:[@media(min-height:640px)]:sticky">
        <SearchFilters v-model="filters" :currency="currency" :has-query="hasQuery" />
      </aside>

      <div>
        <!-- First load of a search: card-shaped placeholders. Later loads dim the old cards. -->
        <div
          v-if="loading && !games.length"
          class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 2xl:grid-cols-5"
          role="status"
          aria-label="Searching"
        >
          <div v-for="n in 8" :key="n" class="skeleton aspect-[3/4]" />
        </div>
        <p v-else-if="loading" class="sr-only" role="status">Searching…</p>
        <p v-else-if="error" class="text-center text-danger" role="alert">⚠️ {{ error }}</p>
        <p v-else-if="searched && games.length === 0" class="text-center text-muted">
          <template v-if="searched.query">
            No games found for "{{ searched.query }}"<template v-if="searched.filtered">
              with these filters</template
            >
          </template>
          <template v-else>No games match these filters</template>
        </p>

        <div v-if="showLanding">
          <WishlistSaleNotice :currency="currency" />
          <RecentlyViewed :currency="currency" />
          <GameSection
            :limit="8"
            title="Top rated deals"
            :currency="currency"
            :filters="TOP_RATED"
          />
          <GameSection
            :limit="8"
            title="New releases on sale"
            :currency="currency"
            :filters="NEW_RELEASES"
            released-only
          />
          <GameSection
            :limit="8"
            title="Free right now"
            :currency="currency"
            :filters="FREE_NOW"
            hide-when-empty
          />
        </div>

        <div
          v-if="games.length"
          class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 2xl:grid-cols-5"
          :class="{ 'opacity-50': loading }"
        >
          <GameCard v-for="game in games" :key="game.gameID" :game="game" />
        </div>

        <div v-if="games.length && !loading && hasMore" class="flex justify-center mt-8">
          <button
            type="button"
            class="px-6 py-3 rounded-xl border focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-60"
            :class="
              loadMoreError
                ? 'border-danger text-danger hover:bg-danger/10'
                : 'border-line-strong bg-surface hover:bg-surface-2'
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

      <aside
        v-reveal
        class="mt-10 lg:col-start-2 xl:col-start-auto xl:mt-0 xl:sticky xl:top-24 xl:self-start"
      >
        <DiscountSidebar :currency="currency" />
      </aside>
    </div>
  </div>
</template>
