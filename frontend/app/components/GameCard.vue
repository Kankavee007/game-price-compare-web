<script setup lang="ts">
import type { Game } from '~/types'

defineProps<{ game: Game }>()
</script>

<template>
  <!-- The card is a wrapper: the link covers the card, the wishlist heart sits on top of it
       as a sibling (a button cannot be inside a link). Hover/focus scale the whole card. -->
  <!-- v-reveal on an outer box: its fade-in transition must not mix with the hover lift below -->
  <div v-reveal>
    <div
      class="group relative rounded-2xl transition duration-300 ease-out hover:-translate-y-1.5 focus-within:-translate-y-1.5"
    >
      <!-- NuxtLink renders a real <a href>: same-tab client-side navigation on click,
         and keyboard, middle-click and "open in new tab" still work -->
      <NuxtLink
        :to="{ path: `/games/${game.gameID}`, query: { currency: game.currency } }"
        class="relative block bg-surface rounded-2xl overflow-hidden ring-1 ring-line shadow-lg shadow-black/30 transition duration-300 group-hover:ring-accent/60 group-hover:shadow-glow focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <GameImage
          :cover="game.cover"
          :thumb="game.thumb"
          :alt="game.name"
          class="w-full aspect-[3/4]"
        />

        <!-- Store label and "Lowest ever" stacked in the top-left corner (cards are narrow on phones) -->
        <span class="absolute top-2 left-2 flex flex-col items-start gap-1">
          <span class="bg-bg/75 backdrop-blur text-xs font-medium px-2 py-1 rounded-lg">
            🏷️ {{ game.storeName ?? 'Store' }}
          </span>
          <LowestBadge v-if="game.isHistoricalLow" />
        </span>

        <div
          class="absolute inset-0 bg-gradient-to-t from-bg via-bg/75 to-transparent opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition duration-300 flex flex-col justify-end p-3"
        >
          <h3 class="text-sm font-semibold">{{ game.name }}</h3>
          <p class="text-success font-display font-bold text-lg">
            💰 {{ game.price }} {{ game.currency }}
          </p>
        </div>
      </NuxtLink>

      <WishlistHeart
        :game="{ gameID: game.gameID, name: game.name, thumb: game.thumb, cover: game.cover }"
        class="absolute top-2 right-2"
      />
    </div>
  </div>
</template>
