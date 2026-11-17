<script setup lang="ts">
// listDeals, emptyFilters (utils/) are auto-imported by Nuxt
import type { Currency, DealFilters, DealResult } from '~/types'

const props = defineProps<{ currency: Currency }>()

const LIMIT = 10
// Biggest discounts only among games Steam players rate 80%+: a plain savings sort is full of
// unknown 95%-off games (checked live 2026-11-15)
const FILTERS: DealFilters = { ...emptyFilters(), sort: 'savings', onSale: true, minRating: 80 }

const deals = ref<DealResult[]>([])
const loading = ref(true)
const error = ref(false)
let controller: AbortController | undefined

async function load() {
  controller?.abort()
  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  error.value = false
  try {
    deals.value = (await listDeals('', props.currency, FILTERS, 0, signal)).results.slice(0, LIMIT)
  } catch {
    if (signal.aborted) return
    deals.value = []
    error.value = true
  }
  loading.value = false
}

watch(() => props.currency, load, { immediate: true })
onBeforeUnmount(() => controller?.abort())

function price(value: number) {
  return `${value.toFixed(2)} ${props.currency}`
}
</script>

<template>
  <section aria-labelledby="discounts-heading">
    <h2 id="discounts-heading" class="text-lg font-bold mb-4">🔥 Biggest discounts</h2>

    <ul v-if="loading" class="space-y-3" role="status" aria-label="Loading">
      <li v-for="n in 5" :key="n" class="h-16 rounded-xl bg-surface animate-pulse" />
    </ul>

    <div
      v-else-if="error"
      class="p-4 rounded-xl border border-danger/40 bg-danger/5 space-y-3"
      role="alert"
    >
      <p class="text-danger">⚠️ Deals unavailable.</p>
      <button
        type="button"
        class="btn-ghost border-danger/60 hover:border-danger hover:text-danger"
        @click="load"
      >
        Try again
      </button>
    </div>

    <p v-else-if="deals.length === 0" class="text-muted">No big discounts right now.</p>

    <ol v-else class="space-y-2">
      <li v-for="deal in deals" :key="deal.gameID">
        <NuxtLink
          :to="{ path: `/games/${deal.gameID}`, query: { currency } }"
          class="flex items-center gap-3 p-2 rounded-xl hover:bg-surface focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <img
            :src="deal.thumb"
            alt=""
            loading="lazy"
            class="w-16 h-8 object-cover rounded-md shrink-0 bg-surface"
          />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium truncate" :title="deal.name">{{ deal.name }}</p>
            <!-- nowrap per price: if both do not fit, the old price moves to the next line whole -->
            <p class="text-sm flex flex-wrap items-baseline gap-x-1">
              <span class="text-success font-semibold whitespace-nowrap">{{
                price(deal.price)
              }}</span>
              <s class="text-subtle text-xs whitespace-nowrap">{{ price(deal.retailPrice) }}</s>
              <LowestBadge v-if="deal.isHistoricalLow" />
            </p>
          </div>
          <span
            class="shrink-0 text-xs font-bold px-2 py-1 rounded bg-danger-strong"
            :aria-label="`${deal.savings}% off`"
            >-{{ deal.savings }}%</span
          >
        </NuxtLink>
      </li>
    </ol>
  </section>
</template>
