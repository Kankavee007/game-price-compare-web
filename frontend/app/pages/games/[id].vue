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

const recent = useRecentlyViewed()

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
    recent.record({
      gameID: id.value,
      name: game.value.name,
      thumb: game.value.thumb,
      cover: game.value.cover,
    })
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
    <NuxtLink to="/" class="text-accent hover:underline" @click="backToSearch"
      >← Back to search</NuxtLink
    >

    <p v-if="loading && !game" class="text-center text-muted" role="status">Loading…</p>

    <div v-else-if="notFound" class="text-center space-y-2 py-16">
      <h1 class="text-3xl font-bold">Game not found</h1>
      <p class="text-muted">There is no game with id "{{ id }}".</p>
    </div>

    <p v-else-if="error" class="text-center text-danger" role="alert">⚠️ {{ error }}</p>

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
              <span class="text-danger font-semibold">♥ In wishlist</span>
              <button
                type="button"
                class="btn-ghost px-3 py-1.5 text-sm"
                @click="wishlist.remove(game.id)"
              >
                Remove from wishlist
              </button>
            </template>
            <button
              v-else
              type="button"
              class="px-4 py-2 rounded-lg bg-danger-strong hover:bg-danger-strong font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              @click="
                wishlist.add({
                  gameID: game.id,
                  name: game.name,
                  thumb: game.thumb,
                  cover: game.cover,
                })
              "
            >
              ♡ Add to wishlist
            </button>
          </div>

          <ul v-if="game.genreTags.length" class="flex flex-wrap gap-2" aria-label="Genres">
            <li v-for="genre in game.genreTags" :key="genre.id">
              <NuxtLink
                :to="{
                  path: '/browse',
                  query: {
                    genre: String(genre.id),
                    ...(currency !== 'USD' && { currency }),
                  },
                }"
                class="block bg-surface-2 hover:bg-line-strong text-sm px-3 py-1 rounded-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                :title="`Browse popular ${genre.name} games`"
                >{{ genre.name }}</NuxtLink
              >
            </li>
          </ul>

          <dl class="flex flex-wrap gap-x-8 gap-y-2 text-fg/80">
            <div v-if="game.rating !== null">
              <dt class="text-xs uppercase text-muted">User rating</dt>
              <dd>
                <span class="font-semibold">{{ game.rating }}/100</span>
                <span v-if="game.ratingCount" class="text-sm">
                  ({{ game.ratingCount }} ratings)</span
                >
              </dd>
            </div>
            <div v-if="game.criticRating !== null">
              <dt class="text-xs uppercase text-muted">Critic rating</dt>
              <dd class="font-semibold">{{ game.criticRating }}/100</dd>
            </div>
            <div v-if="game.releaseDate">
              <dt class="text-xs uppercase text-muted">Released</dt>
              <dd class="text-white">{{ formatDate(game.releaseDate) }}</dd>
            </div>
          </dl>

          <p v-if="game.summary" class="text-fg/80 leading-relaxed">{{ game.summary }}</p>
        </div>
      </section>

      <!-- IGDB screenshots. Hidden when there are none or IGDB failed -->
      <ScreenshotGallery :screenshots="game.screenshots" :game-name="game.name" />

      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <h2 class="text-xl font-semibold">Prices in every store</h2>
        </div>

        <p
          v-if="game.lowestPriceEver !== null"
          class="flex flex-wrap items-center gap-x-3 gap-y-1 text-fg/80"
        >
          <span>
            Lowest ever:
            <span class="font-semibold">{{ formatPrice(game.lowestPriceEver) }}</span>
            <template v-if="game.lowestPriceEverDate">
              on {{ formatDate(game.lowestPriceEverDate) }}</template
            >
          </span>
          <LowestBadge v-if="game.isHistoricalLow" />
          <span v-else-if="aboveLowestPercent !== null && aboveLowestPercent > 0" class="text-sm">
            (cheapest store now is {{ aboveLowestPercent }}% above the lowest price)
          </span>
          <!-- CheapShark stores the lowest price in USD only; we convert it at today's rate -->
          <span v-if="game.currency !== 'USD'" class="basis-full text-xs text-muted">
            Lowest price is recorded in USD and converted at today's exchange rate, so it can differ
            from what it cost in {{ game.currency }} at the time.
          </span>
        </p>

        <PriceAlertForm
          v-if="game.deals.length && game.deals[0]!.price > 0"
          :game-id="game.id"
          :currency="game.currency"
          :current-price="game.deals[0]!.price"
        />

        <p v-if="game.deals.length === 0" class="text-muted">No store sells this game right now.</p>

        <ol v-else class="space-y-2">
          <li v-for="(deal, index) in game.deals" :key="deal.dealUrl">
            <a
              :href="deal.dealUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="panel flex flex-wrap items-center justify-between gap-x-4 gap-y-1 p-4 hover:bg-surface-2/70 hover:border-line-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-accent transition"
              :class="index === 0 ? 'border-success' : 'border-line'"
            >
              <span class="font-semibold">
                {{ deal.storeName ?? 'Unknown store' }}
                <span
                  v-if="index === 0"
                  class="ml-2 text-xs font-bold uppercase bg-success text-bg px-2 py-0.5 rounded"
                  >Cheapest</span
                >
              </span>

              <span class="flex items-baseline gap-3">
                <span v-if="deal.savings > 0" class="text-sm text-success"
                  >-{{ deal.savings }}%</span
                >
                <span v-if="deal.retailPrice > deal.price" class="text-sm text-muted line-through">
                  {{ formatPrice(deal.retailPrice) }}
                </span>
                <span class="text-lg font-bold text-success">{{ formatPrice(deal.price) }}</span>
              </span>
            </a>
          </li>
        </ol>
      </section>

      <!-- IGDB similar games. Hidden when there are none or IGDB failed (prices still show) -->
      <section v-if="game.similarGames.length" aria-labelledby="similar-heading" class="space-y-4">
        <h2 id="similar-heading" class="text-xl font-semibold">Similar games</h2>
        <ul class="grid grid-cols-3 sm:grid-cols-6 gap-4">
          <li v-for="similar in game.similarGames" :key="similar.name">
            <!-- IGDB ids are not CheapShark ids, so search by name -->
            <NuxtLink
              :to="{
                path: '/',
                query: { q: similar.name, ...(currency !== 'USD' && { currency }) },
              }"
              class="block space-y-2 rounded-lg group focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <img
                v-if="similar.cover"
                :src="similar.cover"
                alt=""
                loading="lazy"
                class="w-full aspect-[3/4] object-cover rounded-lg bg-surface group-hover:opacity-80 transition"
              />
              <div
                v-else
                class="w-full aspect-[3/4] rounded-lg bg-surface flex items-center justify-center text-3xl"
                aria-hidden="true"
              >
                🎮
              </div>
              <p class="text-sm leading-snug line-clamp-2 group-hover:underline">
                {{ similar.name }}
              </p>
            </NuxtLink>
          </li>
        </ul>
      </section>
    </article>
  </div>
</template>
