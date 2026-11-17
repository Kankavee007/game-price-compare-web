<script setup lang="ts" generic="T extends string">
// Single-choice dropdown with the same look as StoreSelect, replacing native <select>.
// WAI-ARIA "select-only" listbox: the button opens a listbox that takes focus;
// Up/Down/Home/End move, a letter jumps to the next option starting with it,
// Enter/Space pick, Esc or Tab close (Esc returns focus to the button).
export interface PickOption<V extends string> {
  value: V
  label: string
}

const model = defineModel<T>({ required: true })
const props = defineProps<{
  options: PickOption<T>[]
  /** Accessible name, e.g. "Sort by" */
  label: string
  /** Smaller box for the top bar; the button then shows `short` if given */
  compact?: boolean
  /** Text shown on the button instead of the option label (e.g. just "THB") */
  short?: (option: PickOption<T>) => string
}>()

const uid = useId()
const open = ref(false)
const active = ref(0) // index of the highlighted option while open
const root = ref<HTMLElement | null>(null)
const button = ref<HTMLButtonElement | null>(null)
const list = ref<HTMLElement | null>(null)
const alignRight = ref(false)
const PANEL_MIN_PX = 192

const selectedIndex = computed(() => props.options.findIndex((o) => o.value === model.value))
const selected = computed(() => props.options[selectedIndex.value] ?? props.options[0])
const buttonText = computed(() =>
  selected.value ? (props.short ? props.short(selected.value) : selected.value.label) : '',
)

async function show() {
  const rect = button.value?.getBoundingClientRect()
  alignRight.value =
    !!rect && rect.left + Math.max(rect.width, PANEL_MIN_PX) > window.innerWidth - 8
  active.value = Math.max(selectedIndex.value, 0)
  open.value = true
  await nextTick()
  list.value?.focus()
  scrollActiveIntoView()
}

function hide(returnFocus = true) {
  open.value = false
  if (returnFocus) button.value?.focus()
}

function pick(i: number) {
  const option = props.options[i]
  if (option && option.value !== model.value) model.value = option.value
  hide()
}

function moveTo(i: number) {
  active.value = Math.min(Math.max(i, 0), props.options.length - 1)
  scrollActiveIntoView()
}

function scrollActiveIntoView() {
  nextTick(() =>
    list.value
      ?.querySelector(`#${CSS.escape(optionId(active.value))}`)
      ?.scrollIntoView({ block: 'nearest' }),
  )
}

// Type-ahead: a letter jumps to the next option whose label starts with it
function typeAhead(key: string) {
  const n = props.options.length
  for (let step = 1; step <= n; step++) {
    const i = (active.value + step) % n
    if (props.options[i]?.label.toLowerCase().startsWith(key.toLowerCase())) return moveTo(i)
  }
}

function onListKey(event: KeyboardEvent) {
  switch (event.key) {
    case 'ArrowDown':
      moveTo(active.value + 1)
      break
    case 'ArrowUp':
      moveTo(active.value - 1)
      break
    case 'Home':
      moveTo(0)
      break
    case 'End':
      moveTo(props.options.length - 1)
      break
    case 'Enter':
    case ' ':
      pick(active.value)
      break
    case 'Escape':
      hide()
      break
    case 'Tab':
      hide(false)
      return // let Tab move focus on
    default:
      if (event.key.length === 1 && /\S/.test(event.key)) typeAhead(event.key)
      else return
  }
  event.preventDefault()
}

function optionId(i: number) {
  return `${uid}-opt-${i}`
}

function onPointerDown(event: PointerEvent) {
  if (open.value && !root.value?.contains(event.target as Node)) hide(false)
}

onMounted(() => document.addEventListener('pointerdown', onPointerDown))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPointerDown))
</script>

<template>
  <div ref="root" class="relative">
    <button
      ref="button"
      type="button"
      class="field flex w-full items-center justify-between gap-2 text-left"
      :class="compact ? 'px-2 py-1 text-sm' : 'h-10 px-3 text-sm'"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="`${uid}-list`"
      :aria-label="`${label}: ${selected?.label ?? ''}`"
      @click="open ? hide() : show()"
      @keydown.down.prevent="show()"
      @keydown.up.prevent="show()"
    >
      <span class="truncate">{{ buttonText }}</span>
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
      <ul
        v-if="open"
        :id="`${uid}-list`"
        ref="list"
        role="listbox"
        tabindex="-1"
        :aria-label="label"
        :aria-activedescendant="optionId(active)"
        class="absolute z-30 mt-2 min-w-full w-max max-w-[calc(100vw-2rem)] max-h-72 overflow-y-auto rounded-2xl bg-surface/95 backdrop-blur border border-line shadow-2xl shadow-black/40 p-1.5 focus:outline-none"
        :class="alignRight ? 'right-0' : 'left-0'"
        @keydown="onListKey"
        @blur="hide(false)"
      >
        <li
          v-for="(o, i) in options"
          :id="optionId(i)"
          :key="o.value"
          role="option"
          :aria-selected="o.value === model"
          class="flex items-center gap-3 px-2.5 py-2 rounded-xl text-sm cursor-pointer select-none"
          :class="[
            i === active ? 'bg-surface-2 ring-1 ring-accent/60' : 'hover:bg-surface-2/70',
            o.value === model ? 'text-fg font-semibold' : 'text-muted',
          ]"
          @pointerdown.prevent
          @pointerenter="active = i"
          @click="pick(i)"
        >
          <span class="flex-1 whitespace-nowrap">{{ o.label }}</span>
          <span v-if="o.value === model" aria-hidden="true" class="text-accent">✓</span>
        </li>
      </ul>
    </Transition>
  </div>
</template>
