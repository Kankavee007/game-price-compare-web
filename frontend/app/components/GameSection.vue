<script setup lang="ts">
// listDeals, emptyFilters, filtersToQuery (utils/) are auto-imported by Nuxt
import type { Currency, DealFilters, DealResult } from '~/types'

const props = withDefaults(
  defineProps<{
    title: string
    currency: Currency
    /** Filters for /api/deals; the same filters are used by "See all" on the search page */
    filters: Partial<DealFilters>
    limit?: number
    /** Drop games whose release date is still in the future (CheapShark uses placeholder dates) */
    releasedOnly?: boolean
    /** Hide the whole section when it has no games (instead of an empty message) */
    hideWhenEmpty?: boolean
  }>(),
  { limit: 10, releasedOnly: false, hideWhenEmpty: false },
)

const games = ref<DealResult[]>([])
const loading = ref(true)
const error = ref(false)

const allFilters = computed<DealFilters>(() => ({ ...emptyFilters(), ...props.filters }))
const seeAll = computed(() => ({
  path: '/',
  query: {
    ...(props.currency !== 'USD' && { currency: props.currency }),
    ...filtersToQuery(allFilters.value),
  },
}))

let controller: AbortController | undefined

async function load() {
  controller?.abort()
  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  error.value = false

  try {
    const { results } = await listDeals('', props.currency, allFilters.value, 0, signal)
    const today = new Date().toISOString().slice(0, 10)
    games.value = results
      .filter((g) => !props.releasedOnly || (g.releaseDate !== null && g.releaseDate <= today))
      .slice(0, props.limit)
  } catch {
    if (signal.aborted) return
    games.value = []
    error.value = true
  }
  loading.value = false
}

watch(() => props.currency, load, { immediate: true })
onBeforeUnmount(() => controller?.abort())

const hidden = computed(
  () => props.hideWhenEmpty && !loading.value && !error.value && games.value.length === 0,
)
const headingId = useId()
</script>

<template>
  <section v-if="!hidden" class="mb-10" :aria-labelledby="headingId">
    <div class="flex items-baseline justify-between gap-4 mb-4">
      <h2 :id="headingId" class="text-xl font-bold">{{ title }}</h2>
      <NuxtLink :to="seeAll" class="text-sm text-accent hover:underline shrink-0"
        >See all →</NuxtLink
      >
    </div>

    <!-- Phone: one row that scrolls sideways. md and up: a grid. -->
    <div
      v-if="loading"
      class="flex gap-4 overflow-hidden md:grid md:grid-cols-4"
      role="status"
      aria-label="Loading"
    >
      <div v-for="n in 4" :key="n" class="w-40 shrink-0 md:w-auto skeleton aspect-[3/4]" />
    </div>

    <div
      v-else-if="error"
      class="flex items-center gap-4 p-4 rounded-xl border border-danger/40 bg-danger/5"
      role="alert"
    >
      <p class="text-danger">⚠️ Could not load {{ title.toLowerCase() }}.</p>
      <button
        type="button"
        class="btn-ghost border-danger/60 hover:border-danger hover:text-danger"
        @click="load"
      >
        Try again
      </button>
    </div>

    <p v-else-if="games.length === 0" class="text-muted">No games right now.</p>

    <ul
      v-else
      class="flex gap-4 overflow-x-auto snap-x pb-2 md:grid md:grid-cols-4 md:overflow-visible md:pb-0"
    >
      <li v-for="game in games" :key="game.gameID" class="w-40 shrink-0 snap-start md:w-auto">
        <GameCard :game="game" />
      </li>
    </ul>
  </section>
</template>
