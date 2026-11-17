<script setup lang="ts">
// Portrait game picture that always fills its box without cropping the game art badly.
// 1. cover (portrait, e.g. Steam library_600x900): fills the box (object-cover).
// 2. cover missing or fails (404 for some new Steam games): the landscape thumb is shown whole
//    (object-contain), centered over a blurred copy of itself, so nothing is cut off.
// 3. both missing or fail: a gray placeholder with the game name.
// The parent sets the size (e.g. class="w-full aspect-[3/4]").
const props = defineProps<{
  cover?: string | null
  thumb?: string | null
  alt: string
}>()

type Stage = 'cover' | 'thumb' | 'none'

function firstStage(): Stage {
  if (props.cover) return 'cover'
  if (props.thumb) return 'thumb'
  return 'none'
}

const stage = ref<Stage>(firstStage())
// Same component reused for another game (list re-ordered, new search): start again
watch(
  () => [props.cover, props.thumb],
  () => (stage.value = firstStage()),
)

function onCoverError() {
  stage.value = props.thumb ? 'thumb' : 'none'
}
</script>

<template>
  <div class="relative overflow-hidden bg-surface-2">
    <img
      v-if="stage === 'cover'"
      :src="cover!"
      :alt="alt"
      loading="lazy"
      class="absolute inset-0 w-full h-full object-cover"
      @error="onCoverError"
    />

    <template v-else-if="stage === 'thumb'">
      <img
        :src="thumb!"
        alt=""
        aria-hidden="true"
        loading="lazy"
        class="absolute inset-0 w-full h-full object-cover scale-125 blur-xl opacity-60"
      />
      <img
        :src="thumb!"
        :alt="alt"
        loading="lazy"
        class="absolute inset-0 w-full h-full object-contain"
        @error="stage = 'none'"
      />
    </template>

    <div
      v-else
      role="img"
      :aria-label="alt"
      class="absolute inset-0 flex flex-col items-center justify-center gap-2 p-3 text-center text-muted"
    >
      <span class="text-3xl" aria-hidden="true">🎮</span>
      <span class="text-xs leading-snug line-clamp-3" aria-hidden="true">{{ alt }}</span>
    </div>
  </div>
</template>
