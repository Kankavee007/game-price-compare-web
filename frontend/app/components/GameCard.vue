<script setup lang="ts">
import type { Game } from '~/types'

defineProps<{ game: Game }>()
</script>

<template>
  <!-- The card is a wrapper: the link covers the card, the wishlist heart sits on top of it
       as a sibling (a button cannot be inside a link). Hover/focus scale the whole card. -->
  <div
    class="group relative rounded-2xl hover:scale-105 focus-within:scale-105 transition duration-300"
  >
    <!-- NuxtLink renders a real <a href>: same-tab client-side navigation on click,
         and keyboard, middle-click and "open in new tab" still work -->
    <NuxtLink
      :to="{ path: `/games/${game.gameID}`, query: { currency: game.currency } }"
      class="relative block bg-gray-800 rounded-2xl overflow-hidden shadow-lg group-hover:shadow-blue-500/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <GameImage
        :cover="game.cover"
        :thumb="game.thumb"
        :alt="game.name"
        class="w-full aspect-[3/4]"
      />

      <!-- Store label and "Lowest ever" stacked in the top-left corner (cards are narrow on phones) -->
      <span class="absolute top-2 left-2 flex flex-col items-start gap-1">
        <span class="bg-black/70 text-xs px-2 py-1 rounded">
          🏷️ {{ game.storeName ?? 'Store' }}
        </span>
        <LowestBadge v-if="game.isHistoricalLow" />
      </span>

      <div
        class="absolute inset-0 bg-gradient-to-t from-black via-black/70 to-transparent backdrop-blur-sm opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition duration-300 flex flex-col justify-end p-3"
      >
        <h3 class="text-sm font-semibold">{{ game.name }}</h3>
        <p class="text-green-400 font-bold text-lg">💰 {{ game.price }} {{ game.currency }}</p>
      </div>
    </NuxtLink>

    <WishlistHeart
      :game="{ gameID: game.gameID, name: game.name, thumb: game.thumb, cover: game.cover }"
      class="absolute top-2 right-2"
    />
  </div>
</template>
