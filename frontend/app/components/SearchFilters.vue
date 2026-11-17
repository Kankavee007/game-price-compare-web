<script setup lang="ts">
// getStores, the filter helpers (utils/) are auto-imported by Nuxt
import { SORT_OPTIONS, type DealFilters, type Store } from '~/types'

const filters = defineModel<DealFilters>({ required: true })
const props = defineProps<{ currency: string; hasQuery: boolean }>()

const RATINGS = [70, 80, 90]

// On phone width the panel is folded behind a button; from md up it is always shown
const open = ref(false)
const count = computed(() => activeFilterCount(filters.value))
const rangeError = computed(() => priceRangeError(filters.value))

// The first option is the API default: "Best match" with a search text, else "Best deals".
// "Best match" is never offered without a search text: there is nothing to match against.
const defaultSort = computed(() => (props.hasQuery ? 'relevance' : 'deal'))
const sortChoices = computed(() =>
  SORT_OPTIONS.filter((o) => o.key !== 'relevance' && o.key !== defaultSort.value),
)
const sortValue = computed(() => {
  const sort = filters.value.sort
  return !sort || sort === defaultSort.value || sort === 'relevance' ? '' : sort
})

function update(change: Partial<DealFilters>) {
  filters.value = { ...filters.value, ...change }
}

// The price boxes keep the text as typed ("1." while typing 1.5); the filter gets the number.
// The text is replaced only when the filter changes from outside (Reset, a shared link).
const minText = ref(toText(filters.value.minPrice))
const maxText = ref(toText(filters.value.maxPrice))

watch(
  () => filters.value.minPrice,
  (value) => {
    if (toNumber(minText.value) !== value) minText.value = toText(value)
  },
)
watch(
  () => filters.value.maxPrice,
  (value) => {
    if (toNumber(maxText.value) !== value) maxText.value = toText(value)
  },
)

function onPrice(which: 'minPrice' | 'maxPrice', text: string) {
  if (which === 'minPrice') minText.value = text
  else maxText.value = text
  update({ [which]: toNumber(text) })
}

function toText(value: number | null) {
  return value === null ? '' : String(value)
}

function toNumber(text: string): number | null {
  if (text.trim() === '') return null
  const n = Number(text)
  return Number.isFinite(n) ? n : null
}

function toggleStore(id: string) {
  const stores = filters.value.stores.includes(id)
    ? filters.value.stores.filter((s) => s !== id)
    : [...filters.value.stores, id]
  update({ stores })
}

// Store chips are optional: if the list cannot be loaded they are hidden, other filters still work
const stores = ref<Store[]>([])
const controller = new AbortController()
onMounted(async () => {
  try {
    stores.value = await getStores(controller.signal)
  } catch {
    stores.value = []
  }
})
onBeforeUnmount(() => controller.abort())

function reset() {
  filters.value = emptyFilters()
}
</script>

<template>
  <section aria-label="Filters" class="mb-8">
    <div class="flex items-center gap-3 md:hidden">
      <button
        type="button"
        class="btn-ghost"
        :aria-expanded="open"
        aria-controls="search-filters"
        @click="open = !open"
      >
        Filters<span v-if="count"> ({{ count }})</span>
      </button>
    </div>

    <div
      id="search-filters"
      class="panel mt-3 md:mt-0 space-y-4 p-4"
      :class="open ? 'block' : 'hidden md:block'"
    >
      <div class="flex flex-wrap items-end gap-4">
        <fieldset class="flex items-end gap-2">
          <legend class="text-sm text-muted mb-1">Price ({{ currency }})</legend>
          <input
            :value="minText"
            type="number"
            inputmode="decimal"
            min="0"
            step="any"
            placeholder="Min"
            aria-label="Minimum price"
            class="field w-24 p-2"
            :aria-invalid="!!rangeError"
            aria-describedby="price-error"
            @input="onPrice('minPrice', ($event.target as HTMLInputElement).value)"
          />
          <span class="pb-2 text-subtle">–</span>
          <input
            :value="maxText"
            type="number"
            inputmode="decimal"
            min="0"
            step="any"
            placeholder="Max"
            aria-label="Maximum price"
            class="field w-24 p-2"
            :aria-invalid="!!rangeError"
            aria-describedby="price-error"
            @input="onPrice('maxPrice', ($event.target as HTMLInputElement).value)"
          />
        </fieldset>

        <label class="flex flex-col text-sm text-muted">
          Sort by
          <select
            :value="sortValue"
            class="field mt-1 p-2"
            @change="
              update({
                sort: (($event.target as HTMLSelectElement).value || null) as DealFilters['sort'],
              })
            "
          >
            <option value="">{{ hasQuery ? 'Best match' : 'Best deals' }}</option>
            <option v-for="o in sortChoices" :key="o.key" :value="o.key">{{ o.label }}</option>
          </select>
        </label>

        <label class="flex flex-col text-sm text-muted">
          Steam rating
          <select
            :value="filters.minRating ?? ''"
            class="field mt-1 p-2"
            @change="
              update({
                minRating: toNumber(($event.target as HTMLSelectElement).value),
              })
            "
          >
            <option value="">Any</option>
            <option v-for="r in RATINGS" :key="r" :value="r">{{ r }}%+</option>
          </select>
        </label>

        <label class="flex items-center gap-2 pb-2 cursor-pointer">
          <input
            type="checkbox"
            :checked="filters.onSale"
            class="w-4 h-4 accent-[rgb(var(--c-accent-strong))]"
            @change="update({ onSale: ($event.target as HTMLInputElement).checked })"
          />
          On sale only
        </label>

        <button
          v-if="count"
          type="button"
          class="ml-auto pb-2 text-accent hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
          @click="reset"
        >
          Reset ({{ count }})
        </button>
      </div>

      <p v-if="rangeError" id="price-error" class="text-sm text-danger" role="alert">
        {{ rangeError }}
      </p>

      <div v-if="stores.length" role="group" aria-label="Stores" class="flex flex-wrap gap-2">
        <button
          v-for="s in stores"
          :key="s.storeID"
          type="button"
          :aria-pressed="filters.stores.includes(s.storeID)"
          class="flex items-center gap-1.5 px-3 py-1 rounded-full border text-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          :class="
            filters.stores.includes(s.storeID)
              ? 'bg-accent-strong border-accent text-white'
              : 'bg-bg border-line text-fg/80 hover:border-line-strong'
          "
          @click="toggleStore(s.storeID)"
        >
          <img v-if="s.logo" :src="s.logo" alt="" class="w-4 h-4" loading="lazy" />
          {{ s.storeName }}
        </button>
      </div>
    </div>
  </section>
</template>
