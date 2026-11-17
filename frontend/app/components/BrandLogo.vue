<script setup lang="ts">
// Large areas: the original PixSales logo (mark + wordmark, public/brand/pixsales-logo.png)
// with the tagline under it. Small areas (top bar) use the cropped mark instead.
withDefaults(defineProps<{ tagline?: boolean }>(), { tagline: true })
</script>

<template>
  <div class="flex flex-col items-center gap-2 text-center">
    <img
      src="/brand/pixsales-logo.png"
      alt="PixSales"
      width="1200"
      height="211"
      class="w-full max-w-md h-auto drop-shadow-[0_8px_30px_rgb(var(--c-brand)/0.25)]"
    />
    <p
      v-if="tagline"
      class="font-display text-sm sm:text-base tracking-[0.3em] uppercase text-muted"
    >
      Pixel Perfect Deals
    </p>
  </div>
</template>
