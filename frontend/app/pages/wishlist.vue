<script setup lang="ts">
// getPrices (utils/), useWishlist (composables/) and the components are auto-imported by Nuxt
import { toCurrency, type Currency, type GamePrice, type WishlistItem } from '~/types'

// The page is prerendered (an HTML shell); the list lives in this browser's localStorage, so
// everything below runs in the browser only (<ClientOnly> in the template, onMounted here).

const route = useRoute()
const router = useRouter()
// The currency lives in the URL like on the game page (?currency=THB)
const currency = computed<Currency>({
  get: () => toCurrency(route.query.currency),
  set: (value) => router.replace({ query: { ...route.query, currency: value } }),
})

const wishlist = useWishlist()
const prices = ref<Record<string, GamePrice>>({})
const loadedIds = ref<Set<string>>(new Set()) // ids the last successful request asked for
const loading = ref(false)
const error = ref<string | null>(null)

let controller: AbortController | undefined

async function load() {
  controller?.abort()
  const ids = wishlist.items.value.map((i) => i.gameID)
  if (ids.length === 0) {
    loading.value = false
    error.value = null
    return
  }

  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  error.value = null
  try {
    const list = await getPrices(ids, currency.value, signal)
    prices.value = Object.fromEntries(list.map((p) => [p.gameID, p]))
    loadedIds.value = new Set(ids)
  } catch (err) {
    if (signal.aborted) return
    // Old prices may be in another currency: drop them so nothing wrong is shown
    prices.value = {}
    loadedIds.value = new Set()
    error.value = err instanceof Error ? err.message : 'Something went wrong'
  }
  loading.value = false
}

onMounted(load)
onBeforeUnmount(() => controller?.abort())
watch(currency, load)
// A game added in another tab (or on another page before coming back): load its price.
// Removing a game needs no request, its row just disappears.
watch(
  () => wishlist.items.value.map((i) => i.gameID),
  (ids) => {
    if (ids.some((id) => !loadedIds.value.has(id))) load()
  },
)

type Row = { item: WishlistItem; price: GamePrice | undefined }

// Games on sale first; otherwise keep the wishlist order (newest added first)
const rows = computed<Row[]>(() => {
  const all = wishlist.items.value.map((item) => ({ item, price: prices.value[item.gameID] }))
  const onSale = (r: Row) => (r.price && r.price.savings > 0 ? 0 : 1)
  return [...all].sort((a, b) => onSale(a) - onSale(b))
})

const onSaleCount = computed(() => rows.value.filter((r) => r.price && r.price.savings > 0).length)

function formatPrice(value: number) {
  return `${value.toFixed(2)} ${currency.value}`
}

useHead({ title: 'Wishlist' })
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-3xl font-bold">♥ Wishlist</h1>
    </div>

    <ClientOnly>
      <template #fallback>
        <ul class="space-y-3" role="status" aria-label="Loading your wishlist">
          <li v-for="n in 3" :key="n" class="skeleton h-20" />
        </ul>
      </template>

      <div
        v-if="wishlist.count.value === 0"
        class="text-center py-16 space-y-3 border border-dashed border-line rounded-2xl"
      >
        <p class="text-xl font-semibold">Your wishlist is empty</p>
        <p class="text-muted">Tap ♡ on any game to save it here and keep an eye on its price.</p>
        <NuxtLink to="/" class="inline-block text-accent hover:underline">Find games →</NuxtLink>
      </div>

      <template v-else>
        <p class="text-muted">
          {{ wishlist.count.value }} {{ wishlist.count.value === 1 ? 'game' : 'games' }}
          <template v-if="onSaleCount">· {{ onSaleCount }} on sale</template>
          · saved in this browser only
        </p>

        <div
          v-if="error"
          class="flex flex-wrap items-center gap-4 p-4 rounded-2xl border border-danger/40 bg-danger/10"
          role="alert"
        >
          <p class="text-danger">⚠️ Prices unavailable: {{ error }}</p>
          <button
            type="button"
            class="btn-ghost border-danger/60 hover:border-danger hover:text-danger"
            @click="load"
          >
            Try again
          </button>
        </div>

        <ul class="space-y-3">
          <li
            v-for="{ item, price } in rows"
            :key="item.gameID"
            v-reveal
            class="panel flex flex-wrap sm:flex-nowrap items-center gap-4 p-3"
            :class="price && price.savings > 0 ? 'border-success/50' : 'border-line'"
          >
            <NuxtLink
              :to="{ path: `/games/${item.gameID}`, query: { currency } }"
              class="flex items-center gap-4 min-w-0 flex-1 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              <img
                v-if="item.thumb ?? price?.thumb"
                :src="(item.thumb ?? price?.thumb)!"
                alt=""
                loading="lazy"
                class="w-24 h-12 object-cover rounded-md shrink-0 bg-surface-2"
              />
              <div v-else class="w-24 h-12 rounded-md shrink-0 bg-surface-2" />
              <span class="font-semibold truncate">{{ item.name }}</span>
            </NuxtLink>

            <div class="flex items-center gap-3 ml-auto shrink-0">
              <template v-if="price">
                <div class="text-right">
                  <p class="flex flex-wrap justify-end items-baseline gap-x-2">
                    <span v-if="price.savings > 0" class="text-sm text-success"
                      >-{{ price.savings }}%</span
                    >
                    <s v-if="price.retailPrice > price.price" class="text-sm text-subtle">{{
                      formatPrice(price.retailPrice)
                    }}</s>
                    <span class="text-lg font-bold text-success">{{
                      formatPrice(price.price)
                    }}</span>
                  </p>
                  <p class="flex justify-end items-center gap-2 text-xs text-muted">
                    <LowestBadge v-if="price.isHistoricalLow" />
                    {{ price.storeName ?? 'Unknown store' }}
                  </p>
                </div>
              </template>
              <span v-else-if="loading" class="text-muted text-sm" role="status"
                >Loading price…</span
              >
              <span v-else-if="error" class="text-muted text-sm">Price unavailable</span>
              <span v-else class="text-warn text-sm">No longer listed</span>

              <button
                type="button"
                class="btn-ghost px-3 py-1.5 text-sm"
                :aria-label="`Remove ${item.name} from wishlist`"
                @click="wishlist.remove(item.gameID)"
              >
                Remove
              </button>
            </div>
          </li>
        </ul>
      </template>
    </ClientOnly>
  </div>
</template>
