<script setup lang="ts">
// getGenres, browseGenre, ApiError (utils/) are auto-imported by Nuxt
import { toCurrency, type BrowseGame, type BrowseResult, type Currency, type Genre } from '~/types'

// Prerendered as an app shell like /wishlist; the genre and currency live in the URL
// (/browse?genre=12&currency=THB) so links can be shared and Back works.

const route = useRoute()
const router = useRouter()

const genreParam = computed(() =>
  typeof route.query.genre === 'string' ? route.query.genre.trim() : '',
)
const currency = computed<Currency>({
  get: () => toCurrency(route.query.currency),
  set: (value) => router.replace({ query: { ...route.query, currency: value } }),
})

// --- genre list --------------------------------------------------------------------------
const genres = ref<Genre[]>([])
const genresLoading = ref(true)
const genresError = ref(false)
const genreController = new AbortController()

async function loadGenres() {
  genresLoading.value = true
  genresError.value = false
  try {
    genres.value = await getGenres(genreController.signal)
  } catch {
    if (genreController.signal.aborted) return
    genresError.value = true
  }
  genresLoading.value = false
}

// --- games of the picked genre -----------------------------------------------------------
const result = ref<BrowseResult | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const unknownGenre = ref(false)
let controller: AbortController | undefined

async function loadGames() {
  controller?.abort()
  result.value = null
  error.value = null
  unknownGenre.value = false
  if (!genreParam.value) {
    loading.value = false
    return
  }

  controller = new AbortController()
  const { signal } = controller
  loading.value = true
  try {
    result.value = await browseGenre(genreParam.value, currency.value, signal)
  } catch (err) {
    if (signal.aborted) return
    if (err instanceof ApiError && err.status === 400) unknownGenre.value = true
    else error.value = err instanceof Error ? err.message : 'Something went wrong'
  }
  loading.value = false
}

onMounted(() => {
  loadGenres()
  loadGames()
})
watch([genreParam, currency], loadGames)
onBeforeUnmount(() => {
  genreController.abort()
  controller?.abort()
})

const pickedName = computed(
  () =>
    result.value?.genre.name ??
    genres.value.find((g) => String(g.id) === genreParam.value)?.name ??
    null,
)

function genreLink(id: number) {
  return {
    path: '/browse',
    query: { genre: String(id), ...(currency.value !== 'USD' && { currency: currency.value }) },
  }
}

// Sold on CheapShark: its game page. Not sold: search by name (it may be listed under another name)
function gameLink(game: BrowseGame) {
  return game.gameID
    ? { path: `/games/${game.gameID}`, query: { currency: currency.value } }
    : {
        path: '/',
        query: { q: game.name, ...(currency.value !== 'USD' && { currency: currency.value }) },
      }
}

useHead({ title: () => (pickedName.value ? `Browse ${pickedName.value}` : 'Browse by genre') })
</script>

<template>
  <div class="space-y-8">
    <div class="flex flex-wrap items-center justify-between gap-4">
      <h1 class="text-3xl font-bold">
        Browse <span v-if="pickedName" class="text-accent-2">{{ pickedName }}</span
        ><span v-else>by genre</span>
      </h1>
    </div>

    <!-- Genre list: always shown so another genre is one click away -->
    <section aria-label="Genres">
      <ul v-if="genresLoading" class="flex flex-wrap gap-2" role="status" aria-label="Loading">
        <li v-for="n in 12" :key="n" class="h-8 w-28 rounded-full bg-surface animate-pulse" />
      </ul>
      <div
        v-else-if="genresError"
        class="flex flex-wrap items-center gap-4 p-4 rounded-2xl border border-danger/40 bg-danger/10"
        role="alert"
      >
        <p class="text-danger">⚠️ Genres unavailable.</p>
        <button
          type="button"
          class="btn-ghost border-danger/60 hover:border-danger hover:text-danger"
          @click="loadGenres"
        >
          Try again
        </button>
      </div>
      <ul v-else class="flex flex-wrap gap-2">
        <li v-for="g in genres" :key="g.id">
          <NuxtLink
            :to="genreLink(g.id)"
            class="block px-3 py-1.5 rounded-full border text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            :class="
              String(g.id) === genreParam
                ? 'bg-accent-strong border-accent text-white'
                : 'bg-bg border-line text-fg/80 hover:border-line-strong'
            "
            :aria-current="String(g.id) === genreParam ? 'page' : undefined"
            >{{ g.name }}</NuxtLink
          >
        </li>
      </ul>
    </section>

    <p v-if="!genreParam" class="text-muted">
      Pick a genre to see its most popular PC games and their cheapest price.
    </p>

    <div
      v-else-if="unknownGenre"
      class="p-4 rounded-xl border border-warn/50 bg-warn/5 text-warn"
      role="alert"
    >
      Unknown genre. Pick one from the list above.
    </div>

    <div
      v-else-if="error"
      class="flex flex-wrap items-center gap-4 p-4 rounded-2xl border border-danger/40 bg-danger/10"
      role="alert"
    >
      <p class="text-danger">⚠️ {{ error }}</p>
      <button
        type="button"
        class="btn-ghost border-danger/60 hover:border-danger hover:text-danger"
        @click="loadGames"
      >
        Try again
      </button>
    </div>

    <ul
      v-else-if="loading"
      class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4"
      role="status"
      aria-label="Loading"
    >
      <li v-for="n in 8" :key="n" class="h-80 rounded-2xl bg-surface animate-pulse" />
    </ul>

    <p v-else-if="result && result.games.length === 0" class="text-muted">
      No games found for this genre.
    </p>

    <ul v-else-if="result" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <li v-for="game in result.games" :key="game.name">
        <NuxtLink
          :to="gameLink(game)"
          class="panel flex flex-col h-full overflow-hidden hover:border-accent/60 hover:shadow-glow hover:-translate-y-1 duration-300 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <img
            v-if="game.cover"
            :src="game.cover"
            alt=""
            loading="lazy"
            class="w-full aspect-[3/4] object-cover bg-surface-2"
          />
          <div
            v-else
            class="w-full aspect-[3/4] bg-surface-2 flex items-center justify-center text-4xl"
            aria-hidden="true"
          >
            🎮
          </div>
          <div class="flex flex-col flex-1 gap-1 p-3">
            <p class="font-semibold leading-snug line-clamp-2">{{ game.name }}</p>
            <p v-if="game.rating !== null" class="text-xs text-muted">
              Rating {{ game.rating }}/100
            </p>
            <p v-if="game.price !== null" class="mt-auto text-lg font-bold text-success">
              {{ game.price.toFixed(2) }} {{ result.currency }}
            </p>
            <p v-else class="mt-auto text-sm text-muted">Not sold in tracked stores</p>
          </div>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>
