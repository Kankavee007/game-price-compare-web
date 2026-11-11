<script setup lang="ts">
// searchGames (utils/) and the components are auto-imported by Nuxt
import type { Currency, Game } from '~/types'

const DEBOUNCE_MS = 500

const query = ref('')
const currency = ref<Currency>('USD')
const games = ref<Game[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const searchedFor = ref<string | null>(null) // query of the last finished search

let timer: ReturnType<typeof setTimeout> | undefined
let controller: AbortController | undefined

async function runSearch() {
  const q = query.value.trim()

  // Cancel the previous request so a slow old response can't overwrite a newer one
  controller?.abort()

  if (!q) {
    games.value = []
    error.value = null
    searchedFor.value = null
    loading.value = false
    return
  }

  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  error.value = null

  try {
    games.value = await searchGames(q, currency.value, signal)
  } catch (err) {
    if (signal.aborted) return
    games.value = []
    error.value = err instanceof Error ? err.message : 'Something went wrong'
  }
  loading.value = false
  searchedFor.value = q
}

watch([query, currency], () => {
  clearTimeout(timer)
  timer = setTimeout(runSearch, DEBOUNCE_MS)
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
      class="w-full p-3 rounded-xl bg-gray-800 border border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 mb-8"
    />

    <p v-if="loading" class="text-center text-gray-400" role="status">Searching…</p>
    <p v-else-if="error" class="text-center text-red-400" role="alert">⚠️ {{ error }}</p>
    <p v-else-if="searchedFor && games.length === 0" class="text-center text-gray-400">
      No games found for "{{ searchedFor }}"
    </p>

    <div
      v-if="games.length"
      class="grid gap-6 grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      :class="{ 'opacity-50': loading }"
    >
      <GameCard v-for="game in games" :key="game.dealUrl" :game="game" />
    </div>
  </div>
</template>
