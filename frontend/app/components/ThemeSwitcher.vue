<script setup lang="ts">
import { THEMES, type ThemeId } from '~/composables/useTheme'

// Palette button in the top bar with a small menu of color presets (WAI-ARIA menu button:
// Enter/Space/ArrowDown open it, arrows move, Enter/Space pick, Esc closes, focus returns).
const theme = useTheme()

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const items = ref<HTMLButtonElement[]>([])

// The menu (12rem) opens under the button toward the left; if the button sits near the left
// edge (top bar wrapped on a narrow phone) it opens toward the right instead
const alignLeft = ref(false)
const MENU_PX = 192

async function show(focusIndex?: number) {
  const rect = button.value?.getBoundingClientRect()
  alignLeft.value = !!rect && rect.right - MENU_PX < 8
  open.value = true
  await nextTick()
  const i = focusIndex ?? THEMES.findIndex((t) => t.id === theme.current.value)
  items.value[Math.max(i, 0)]?.focus()
}

function hide(returnFocus = true) {
  open.value = false
  if (returnFocus) button.value?.focus()
}

function pick(id: ThemeId) {
  theme.set(id)
  hide()
}

function move(step: number) {
  const i = items.value.indexOf(document.activeElement as HTMLButtonElement)
  const next = (i + step + items.value.length) % items.value.length
  items.value[next]?.focus()
}

function onPointerDown(event: PointerEvent) {
  if (open.value && !root.value?.contains(event.target as Node)) hide(false)
}

function onFocusOut(event: FocusEvent) {
  const next = event.relatedTarget as Node | null
  if (open.value && next && !root.value?.contains(next)) hide(false)
}

onMounted(() => {
  theme.sync()
  document.addEventListener('pointerdown', onPointerDown)
})
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPointerDown))
</script>

<template>
  <div ref="root" class="relative" @focusout="onFocusOut" @keydown.esc.stop="open && hide()">
    <button
      ref="button"
      type="button"
      class="grid place-items-center w-9 h-9 rounded-xl text-muted hover:text-fg hover:bg-surface-2/70 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      aria-label="Color theme"
      aria-haspopup="menu"
      :aria-expanded="open"
      aria-controls="theme-menu"
      @click="open ? hide() : show()"
      @keydown.down.prevent="show()"
      @keydown.up.prevent="show(THEMES.length - 1)"
    >
      <span aria-hidden="true" class="text-lg">🎨</span>
    </button>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1 scale-[0.98]"
      leave-active-class="transition duration-100 ease-in"
      leave-to-class="opacity-0 -translate-y-1 scale-[0.98]"
    >
      <div
        v-if="open"
        id="theme-menu"
        role="menu"
        :class="alignLeft ? 'left-0' : 'right-0'"
        aria-label="Color theme"
        class="absolute z-40 mt-2 w-48 rounded-2xl bg-surface/95 backdrop-blur border border-line shadow-2xl shadow-black/40 p-1.5"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.home.prevent="items[0]?.focus()"
        @keydown.end.prevent="items[items.length - 1]?.focus()"
      >
        <button
          v-for="t in THEMES"
          :key="t.id"
          ref="items"
          type="button"
          role="menuitemradio"
          :aria-checked="theme.current.value === t.id"
          class="flex w-full items-center gap-3 px-2.5 py-2 rounded-xl text-sm text-left hover:bg-surface-2/80 focus:outline-none focus-visible:bg-surface-2 focus-visible:ring-2 focus-visible:ring-accent"
          :class="theme.current.value === t.id ? 'text-fg font-semibold' : 'text-muted'"
          @click="pick(t.id)"
        >
          <span class="flex -space-x-1" aria-hidden="true">
            <span
              v-for="c in t.swatches"
              :key="c"
              class="w-4 h-4 rounded-full ring-2 ring-surface"
              :style="{ backgroundColor: c }"
            />
          </span>
          <span class="flex-1">{{ t.label }}</span>
          <span v-if="theme.current.value === t.id" aria-hidden="true" class="text-accent">✓</span>
        </button>
      </div>
    </Transition>
  </div>
</template>
