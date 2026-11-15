<script setup lang="ts">
// getGameDetail, ApiError (utils/) and the components are auto-imported by Nuxt
import { toCurrency, type Currency, type GameDetail } from '~/types'

const route = useRoute()
const router = useRouter()

const id = computed(() => String(route.params.id))
// The currency lives in the URL (?currency=THB) so a link from search keeps it and a reload too
const currency = computed<Currency>({
  get: () => toCurrency(route.query.currency),
  set: (value) => router.replace({ query: { ...route.query, currency: value } }),
})

const game = ref<GameDetail | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const notFound = ref(false)

let controller: AbortController | undefined

async function load() {
  // Cancel the previous request so a slow old response can't overwrite a newer one
  controller?.abort()
  controller = new AbortController()
  const { signal } = controller

  loading.value = true
  error.value = null
  notFound.value = false

  try {
    game.value = await getGameDetail(id.value, currency.value, signal)
  } catch (err) {
    if (signal.aborted) return
    game.value = null
    if (err instanceof ApiError && err.status === 404) notFound.value = true
    else error.value = err instanceof Error ? err.message : 'Something went wrong'
  }
  loading.value = false
}

// immediate: load on first visit, then again when the currency (or the game) changes
watch([id, currency], load, { immediate: true })
onBeforeUnmount(() => controller?.abort())

useHead({
  title: () => game.value?.name ?? (notFound.value ? 'Game not found' : ''),
})

const wishlist = useWishlist()
const inWishlist = computed(() => wishlist.has(id.value))

const image = computed(() => game.value?.cover ?? game.value?.thumb ?? null)

// Came from the search page: go back in history so its search (kept in the URL) comes back.
// Opened directly (new tab, shared link): there is no history to go back to, so follow the link to /.
function backToSearch(event: MouseEvent) {
  if (window.history.state?.back) {
    event.preventDefault()
    router.back()
  }
}

// "12% above the lowest price": today's cheapest store against the lowest price ever.
// null when there is nothing to compare (no data, no deals, or the lowest ever was free).
const aboveLowestPercent = computed(() => {
  const g = game.value
  const cheapest = g?.deals[0]?.price
  if (!g || g.isHistoricalLow || !g.lowestPriceEver || cheapest === undefined) return null
  return Math.round(((cheapest - g.lowestPriceEver) / g.lowestPriceEver) * 100)
})

function formatPrice(value: number) {
  return `${value.toFixed(2)} ${game.value?.currency ?? ''}`
}

function formatDate(isoDate: string) {
  // UTC on both sides, so "2011-04-19" never shows as the 18th in timezones behind UTC
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  })
}
</script>

<template>
  <div class="space-y-8">
    <NuxtLink to="/" class="text-blue-400 hover:underline" @click="backToSearch"
      >← Back to search</NuxtLink
    >

    <p v-if="loading && !game" class="text-center text-gray-400" role="status">Loading…</p>

    <div v-else-if="notFound" class="text-center space-y-2 py-16">
      <h1 class="text-3xl font-bold">Game not found</h1>
      <p class="text-gray-400">There is no game with id "{{ id }}".</p>
    </div>

    <p v-else-if="error" class="text-center text-red-400" role="alert">⚠️ {{ error }}</p>

    <article v-else-if="game" class="space-y-8" :class="{ 'opacity-50': loading }">
      <!-- Info: cover above text on phones, side by side from sm up -->
      <section class="flex flex-col sm:flex-row gap-6">
        <img
          v-if="image"
          :src="image"
          :alt="`${game.name} cover`"
          class="w-48 max-w-full self-center sm:self-start rounded-xl shadow-lg object-cover"
        />

        <div class="space-y-3 min-w-0">
          <h1 class="text-3xl font-bold break-words">{{ game.name }}</h1>

          <div class="flex flex-wrap items-center gap-3">
            <template v-if="inWishlist">
              <span class="text-red-400 font-semibold">♥ In wishlist</span>
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg border border-gray-600 text-sm hover:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                @click="wishlist.remove(game.id)"
              >
                Remove from wishlist
              </button>
            </template>
            <button
              v-else
              type="button"
              class="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              @click="
                wishlist.add({ gameID: game.id, name: game.name, thumb: game.thumb ?? game.cover })
              "
            >
              ♡ Add to wishlist
            </button>
          </div>

          <ul v-if="game.genres.length" class="flex flex-wrap gap-2" aria-label="Genres">
            <li
              v-for="genre in game.genres"
              :key="genre"
              class="bg-gray-700 text-sm px-3 py-1 rounded-full"
            >
              {{ genre }}
            </li>
          </ul>

          <dl class="flex flex-wrap gap-x-8 gap-y-2 text-gray-300">
            <div v-if="game.rating !== null">
              <dt class="text-xs uppercase text-gray-400">User rating</dt>
              <dd>
                <span class="text-white font-semibold">{{ game.rating }}/100</span>
                <span v-if="game.ratingCount" class="text-sm">
                  ({{ game.ratingCount }} ratings)</span
                >
              </dd>
            </div>
            <div v-if="game.criticRating !== null">
              <dt class="text-xs uppercase text-gray-400">Critic rating</dt>
              <dd class="text-white font-semibold">{{ game.criticRating }}/100</dd>
            </div>
            <div v-if="game.releaseDate">
              <dt class="text-xs uppercase text-gray-400">Released</dt>
              <dd class="text-white">{{ formatDate(game.releaseDate) }}</dd>
            </div>
          </dl>

          <p v-if="game.summary" class="text-gray-300 leading-relaxed">{{ game.summary }}</p>
        </div>
      </section>

      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <h2 class="text-xl font-semibold">Prices in every store</h2>
          <CurrencySelect v-model="currency" />
        </div>

        <p
          v-if="game.lowestPriceEver !== null"
          class="flex flex-wrap items-center gap-x-3 gap-y-1 text-gray-300"
        >
          <span>
            Lowest ever:
            <span class="font-semibold text-white">{{ formatPrice(game.lowestPriceEver) }}</span>
            <template v-if="game.lowestPriceEverDate">
              on {{ formatDate(game.lowestPriceEverDate) }}</template
            >
          </span>
          <LowestBadge v-if="game.isHistoricalLow" />
          <span v-else-if="aboveLowestPercent !== null && aboveLowestPercent > 0" class="text-sm">
            (cheapest store now is {{ aboveLowestPercent }}% above the lowest price)
          </span>
          <!-- CheapShark stores the lowest price in USD only; we convert it at today's rate -->
          <span v-if="game.currency !== 'USD'" class="basis-full text-xs text-gray-400">
            Lowest price is recorded in USD and converted at today's exchange rate, so it can differ
            from what it cost in {{ game.currency }} at the time.
          </span>
        </p>

        <p v-if="game.deals.length === 0" class="text-gray-400">
          No store sells this game right now.
        </p>

        <ol v-else class="space-y-2">
          <li v-for="(deal, index) in game.deals" :key="deal.dealUrl">
            <a
              :href="deal.dealUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 border focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition"
              :class="index === 0 ? 'border-green-500' : 'border-gray-700'"
            >
              <span class="font-semibold">
                {{ deal.storeName ?? 'Unknown store' }}
                <span
                  v-if="index === 0"
                  class="ml-2 text-xs font-bold uppercase bg-green-500 text-gray-900 px-2 py-0.5 rounded"
                  >Cheapest</span
                >
              </span>

              <span class="flex items-baseline gap-3">
                <span v-if="deal.savings > 0" class="text-sm text-green-400"
                  >-{{ deal.savings }}%</span
                >
                <span
                  v-if="deal.retailPrice > deal.price"
                  class="text-sm text-gray-400 line-through"
                >
                  {{ formatPrice(deal.retailPrice) }}
                </span>
                <span class="text-lg font-bold text-green-400">{{ formatPrice(deal.price) }}</span>
              </span>
            </a>
          </li>
        </ol>
      </section>
    </article>
  </div>
</template>
