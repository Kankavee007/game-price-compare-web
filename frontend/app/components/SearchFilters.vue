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
// Options for the dropdowns; '' is the default choice (no filter / API default sort)
const sortPickOptions = computed(() => [
  { value: '', label: props.hasQuery ? 'Best match' : 'Best deals' },
  ...sortChoices.value.map((o) => ({ value: o.key as string, label: o.label })),
])
const ratingPickOptions = [
  { value: '', label: 'Any' },
  ...RATINGS.map((r) => ({ value: String(r), label: `${r}%+` })),
]

const sortValue = computed<string>(() => {
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

// The store filter is optional: if the list cannot be loaded its button says so and is
// disabled, the other filters still work
const stores = ref<Store[]>([])
const storeStatus = ref<'loading' | 'ready' | 'error'>('loading')
const controller = new AbortController()
onMounted(async () => {
  try {
    stores.value = await getStores(controller.signal)
    storeStatus.value = 'ready'
  } catch {
    if (!controller.signal.aborted) storeStatus.value = 'error'
  }
})
onBeforeUnmount(() => controller.abort())

function reset() {
  filters.value = emptyFilters()
}
</script>

<template>
  <!-- relative z-10: the dropdowns open over the results. lg+: it sits in the search page's
       left sidebar, so the boxes stack in one column -->
  <section aria-label="Filters" class="relative z-10 mb-8 lg:mb-0">
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
      <!-- Four equal boxes: one per row on phones, two on tablets, one column in the lg sidebar -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4">
        <fieldset class="flex flex-col gap-1 min-w-0">
          <legend class="text-sm text-muted mb-1">Price ({{ currency }})</legend>
          <!-- Min and max share one box, the same size as the dropdowns -->
          <div
            class="field flex h-10 items-center gap-1 px-3 focus-within:ring-2 focus-within:ring-accent focus-within:border-transparent"
            :class="{ '!border-danger': rangeError }"
          >
            <input
              :value="minText"
              type="number"
              inputmode="decimal"
              min="0"
              step="any"
              placeholder="Min"
              aria-label="Minimum price"
              class="w-full min-w-0 bg-transparent text-sm placeholder:text-subtle focus:outline-none"
              :aria-invalid="!!rangeError"
              aria-describedby="price-error"
              @input="onPrice('minPrice', ($event.target as HTMLInputElement).value)"
            />
            <span class="text-subtle" aria-hidden="true">–</span>
            <input
              :value="maxText"
              type="number"
              inputmode="decimal"
              min="0"
              step="any"
              placeholder="Max"
              aria-label="Maximum price"
              class="w-full min-w-0 bg-transparent text-sm text-right placeholder:text-subtle focus:outline-none"
              :aria-invalid="!!rangeError"
              aria-describedby="price-error"
              @input="onPrice('maxPrice', ($event.target as HTMLInputElement).value)"
            />
          </div>
        </fieldset>

        <div class="flex flex-col gap-1 min-w-0 text-sm text-muted">
          <span aria-hidden="true">Sort by</span>
          <PickSelect
            label="Sort by"
            :model-value="sortValue"
            :options="sortPickOptions"
            @update:model-value="update({ sort: ($event || null) as DealFilters['sort'] })"
          />
        </div>

        <div class="flex flex-col gap-1 min-w-0 text-sm text-muted">
          <span aria-hidden="true">Steam rating</span>
          <PickSelect
            label="Steam rating"
            :model-value="filters.minRating === null ? '' : String(filters.minRating)"
            :options="ratingPickOptions"
            @update:model-value="update({ minRating: toNumber($event) })"
          />
        </div>

        <div class="flex flex-col gap-1 min-w-0 text-sm text-muted">
          <span aria-hidden="true">Stores</span>
          <StoreSelect
            :model-value="filters.stores"
            :stores="stores"
            :status="storeStatus"
            @update:model-value="update({ stores: $event })"
          />
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <label class="flex items-center gap-2 text-sm cursor-pointer">
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
          class="ml-auto text-sm text-accent hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
          @click="reset"
        >
          Reset ({{ count }})
        </button>
      </div>

      <p v-if="rangeError" id="price-error" class="text-sm text-danger" role="alert">
        {{ rangeError }}
      </p>
    </div>
  </section>
</template>
