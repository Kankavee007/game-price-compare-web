<script setup lang="ts">
import type { Currency } from '~/types'

// "Your wishlist: 2 games on sale" on the landing page. Silent when the wishlist is empty,
// nothing is on sale, or the price request fails: it is a hint, not part of the page.
const props = defineProps<{ currency: Currency }>()

const wishlist = useWishlist()
const onSale = ref(0)
let controller: AbortController | undefined

async function load() {
  controller?.abort()
  const ids = wishlist.items.value.map((i) => i.gameID)
  if (ids.length === 0) {
    onSale.value = 0
    return
  }
  controller = new AbortController()
  const { signal } = controller
  try {
    const prices = await getPrices(ids, props.currency, signal)
    onSale.value = prices.filter((p) => p.savings > 0).length
  } catch {
    if (!signal.aborted) onSale.value = 0
  }
}

onMounted(load)
onBeforeUnmount(() => controller?.abort())
watch(() => wishlist.items.value.map((i) => i.gameID).join(','), load)
</script>

<template>
  <NuxtLink
    v-if="onSale > 0"
    to="/wishlist"
    class="flex items-center justify-between gap-4 mb-8 p-4 rounded-xl border border-red-500/50 bg-red-500/10 hover:bg-red-500/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
  >
    <span>
      <span class="text-red-400" aria-hidden="true">♥</span>
      Your wishlist: <strong>{{ onSale }} {{ onSale === 1 ? 'game' : 'games' }} on sale</strong>
    </span>
    <span class="text-blue-300 shrink-0">See wishlist →</span>
  </NuxtLink>
</template>
