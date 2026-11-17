<script setup lang="ts">
import type { Store } from '~/types'

// Store filter as a dropdown: a button that opens a panel with a search box,
// Select all / Clear and one checkbox per store. No store ticked means every store.
const selected = defineModel<string[]>({ required: true })
const props = defineProps<{ stores: Store[]; status: 'loading' | 'ready' | 'error' }>()

const open = ref(false)
const search = ref('')
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const searchBox = ref<HTMLInputElement | null>(null)

const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return q ? props.stores.filter((s) => s.storeName.toLowerCase().includes(q)) : props.stores
})

const label = computed(() => {
  if (props.status === 'loading') return 'Stores…'
  if (props.status === 'error') return 'Stores unavailable'
  return selected.value.length ? `Stores (${selected.value.length})` : 'All stores'
})

function toggle(id: string, checked: boolean) {
  selected.value = checked ? [...selected.value, id] : selected.value.filter((s) => s !== id)
}

// Select all adds the stores shown now, so "hum" + Select all ticks only Humble Store
function selectAll() {
  const ids = new Set(selected.value)
  for (const s of visible.value) ids.add(s.storeID)
  selected.value = [...ids]
}

function clear() {
  selected.value = []
}

// Open toward the left when the panel (18rem) would run past the right edge of the screen
const alignRight = ref(false)
const PANEL_PX = 288

async function show() {
  const rect = button.value?.getBoundingClientRect()
  alignRight.value = !!rect && rect.left + PANEL_PX > window.innerWidth - 16
  open.value = true
  await nextTick()
  searchBox.value?.focus()
}

function hide(returnFocus = true) {
  open.value = false
  search.value = ''
  if (returnFocus) button.value?.focus()
}

// Click or tap anywhere outside the button and panel: close without moving focus
function onPointerDown(event: PointerEvent) {
  if (open.value && !root.value?.contains(event.target as Node)) hide(false)
}

// Tab moved focus out of the whole dropdown: close
function onFocusOut(event: FocusEvent) {
  const next = event.relatedTarget as Node | null
  if (open.value && next && !root.value?.contains(next)) hide(false)
}

onMounted(() => document.addEventListener('pointerdown', onPointerDown))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPointerDown))
</script>

<template>
  <div ref="root" class="relative" @focusout="onFocusOut" @keydown.esc.stop="open && hide()">
    <button
      ref="button"
      type="button"
      class="field flex w-full h-10 items-center justify-between gap-2 px-3 text-sm text-left disabled:opacity-60 disabled:cursor-not-allowed"
      :class="selected.length ? 'border-accent/60 text-fg' : ''"
      :disabled="status !== 'ready' || !stores.length"
      :aria-expanded="open"
      aria-haspopup="true"
      aria-controls="store-select-panel"
      @click="open ? hide() : show()"
    >
      <span class="truncate">{{ label }}</span>
      <span
        aria-hidden="true"
        class="text-xs text-muted transition-transform"
        :class="{ 'rotate-180': open }"
        >▾</span
      >
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1 scale-[0.98]"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0 -translate-y-1 scale-[0.98]"
    >
      <div
        v-if="open"
        id="store-select-panel"
        :class="alignRight ? 'right-0' : 'left-0'"
        role="group"
        aria-label="Stores"
        class="absolute z-20 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-2xl bg-surface/95 backdrop-blur border border-line shadow-2xl shadow-black/40 p-3 space-y-2"
      >
        <input
          ref="searchBox"
          v-model="search"
          type="search"
          placeholder="Find a store…"
          aria-label="Find a store"
          class="field w-full px-3 py-2 text-sm"
        />
        <div class="flex items-center justify-between text-sm">
          <button
            type="button"
            class="text-accent hover:underline rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            @click="selectAll"
          >
            Select all
          </button>
          <button
            type="button"
            class="text-muted hover:text-fg rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"
            :disabled="!selected.length"
            @click="clear"
          >
            Clear
          </button>
        </div>

        <ul class="max-h-64 overflow-y-auto -mx-1 pr-1 space-y-0.5">
          <li v-for="s in visible" :key="s.storeID">
            <label
              class="flex items-center gap-2.5 px-2 py-1.5 rounded-lg cursor-pointer text-sm hover:bg-surface-2/80 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-accent"
            >
              <input
                type="checkbox"
                class="w-4 h-4 accent-[rgb(var(--c-accent-strong))]"
                :checked="selected.includes(s.storeID)"
                @change="toggle(s.storeID, ($event.target as HTMLInputElement).checked)"
              />
              <img v-if="s.logo" :src="s.logo" alt="" class="w-4 h-4" loading="lazy" />
              <span v-else class="w-4 h-4" aria-hidden="true" />
              {{ s.storeName }}
            </label>
          </li>
          <li v-if="!visible.length" class="px-2 py-3 text-sm text-muted" role="status">
            No store matches “{{ search.trim() }}”
          </li>
        </ul>
      </div>
    </Transition>
  </div>
</template>
