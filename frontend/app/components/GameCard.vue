<script setup lang="ts">
import type { Game } from '~/types'

defineProps<{ game: Game }>()
</script>

<template>
  <!-- NuxtLink renders a real <a href>: same-tab client-side navigation on click,
       and keyboard, middle-click and "open in new tab" still work -->
  <NuxtLink
    :to="{ path: `/games/${game.gameID}`, query: { currency: game.currency } }"
    class="group relative block bg-gray-800 rounded-2xl overflow-hidden shadow-lg hover:scale-105 focus-visible:scale-105 hover:shadow-blue-500/20 transition duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
  >
    <img :src="game.thumb" :alt="game.name" loading="lazy" class="w-full h-60 object-cover" />

    <span class="absolute top-2 left-2 bg-black/70 text-xs px-2 py-1 rounded">
      🏷️ {{ game.storeName ?? 'Store' }}
    </span>

    <div
      class="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-transparent backdrop-blur-sm opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100 transition duration-300 flex flex-col justify-end p-3"
    >
      <h3 class="text-sm font-semibold">{{ game.name }}</h3>
      <p class="text-green-400 font-bold text-lg">💰 {{ game.price }} {{ game.currency }}</p>
    </div>
  </NuxtLink>
</template>
