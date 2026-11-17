<script setup lang="ts">
// IGDB screenshots on the detail page: a strip that scrolls sideways, and a full-size view.
// The full view is a native <dialog> opened with showModal(): the browser keeps focus inside it,
// closes it on Esc and puts focus back on the tile that opened it.
import type { Screenshot } from '~/types'

const props = defineProps<{ screenshots: Screenshot[]; gameName: string }>()

// Tiles whose image failed to load are hidden; the rest still show
const failed = ref(new Set<string>())
const shown = computed(() => props.screenshots.filter((s) => !failed.value.has(s.thumb)))

function hide(shot: Screenshot) {
  failed.value = new Set(failed.value).add(shot.thumb)
}

const dialog = ref<HTMLDialogElement | null>(null)
const current = ref(0)
const active = computed(() => shown.value[current.value] ?? null)

function open(index: number) {
  current.value = index
  dialog.value?.showModal()
}

function close() {
  dialog.value?.close()
}

function move(step: number) {
  const count = shown.value.length
  if (count) current.value = (current.value + step + count) % count
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowRight') move(1)
  else if (event.key === 'ArrowLeft') move(-1)
  else return
  event.preventDefault()
}

// A click on the dark area around the picture lands on the <dialog> itself
function onDialogClick(event: MouseEvent) {
  if (event.target === dialog.value) close()
}

// The full image failed (e.g. no 1080p size): hide it from the strip and show the next one
function onFullError() {
  if (!active.value) return
  hide(active.value)
  if (!shown.value.length) close()
  else if (current.value >= shown.value.length) current.value = 0
}

// A new game loaded while the view was open (e.g. back/forward): close it
watch(
  () => props.screenshots,
  () => {
    failed.value = new Set()
    close()
  },
)
</script>

<template>
  <!-- No space-y-* here: it would set margin-top/bottom on the <dialog> and undo its m-auto
       centering, so the heading gets its own margin -->
  <section v-if="shown.length" aria-labelledby="screenshots-heading">
    <h2 id="screenshots-heading" class="text-xl font-semibold mb-4">Screenshots</h2>

    <ul
      class="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 [scrollbar-color:#4b5563_transparent]"
    >
      <li v-for="(shot, index) in shown" :key="shot.thumb" class="w-64 sm:w-80 shrink-0 snap-start">
        <button
          type="button"
          class="block w-full rounded-lg overflow-hidden bg-surface hover:opacity-80 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          :aria-label="`Open screenshot ${index + 1} of ${shown.length}`"
          @click="open(index)"
        >
          <img
            :src="shot.thumb"
            alt=""
            loading="lazy"
            class="w-full aspect-video object-cover"
            @error="hide(shot)"
          />
        </button>
      </li>
    </ul>

    <dialog
      ref="dialog"
      class="m-auto w-full max-w-6xl bg-transparent p-0 backdrop:bg-black/85"
      :aria-label="`${gameName} screenshots`"
      @click="onDialogClick"
      @keydown="onKeydown"
    >
      <figure v-if="active" class="relative px-2 sm:px-14">
        <img
          :key="active.full"
          :src="active.full"
          :alt="`${gameName} screenshot ${current + 1} of ${shown.length}`"
          class="w-full max-h-[85vh] object-contain rounded-lg"
          @error="onFullError"
        />
        <figcaption class="mt-2 text-center text-sm text-fg/80">
          {{ current + 1 }} / {{ shown.length }}
        </figcaption>

        <button
          type="button"
          class="absolute top-2 right-4 sm:right-16 w-10 h-10 rounded-full bg-white/15 hover:bg-white/30 text-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          aria-label="Close"
          @click="close"
        >
          ✕
        </button>
        <template v-if="shown.length > 1">
          <button
            type="button"
            class="absolute left-3 sm:left-0 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/15 hover:bg-white/30 text-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            aria-label="Previous screenshot"
            @click="move(-1)"
          >
            ‹
          </button>
          <button
            type="button"
            class="absolute right-3 sm:right-0 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/15 hover:bg-white/30 text-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            aria-label="Next screenshot"
            @click="move(1)"
          >
            ›
          </button>
        </template>
      </figure>
    </dialog>
  </section>
</template>
