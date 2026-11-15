<script setup lang="ts">
// Games opened in this browser (useRecentlyViewed). No price, so no API call: the cards show
// only the picture and the name. Same row/grid layout as GameSection.
const props = defineProps<{ currency: string }>()

const recent = useRecentlyViewed()
const query = computed(() => (props.currency !== 'USD' ? { currency: props.currency } : {}))
</script>

<template>
  <section v-if="recent.items.value.length" class="mb-10" aria-labelledby="recent-heading">
    <div class="flex items-baseline justify-between gap-4 mb-4">
      <h2 id="recent-heading" class="text-xl font-bold">Recently viewed</h2>
      <button
        type="button"
        class="text-sm text-blue-400 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        @click="recent.clear()"
      >
        Clear
      </button>
    </div>

    <ul
      class="flex gap-4 overflow-x-auto snap-x pb-2 md:grid md:grid-cols-4 md:overflow-visible md:pb-0"
    >
      <li
        v-for="game in recent.items.value"
        :key="game.gameID"
        class="w-40 shrink-0 snap-start md:w-auto"
      >
        <NuxtLink
          :to="{ path: `/games/${game.gameID}`, query }"
          class="block rounded-xl overflow-hidden bg-gray-800 hover:bg-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <img
            v-if="game.thumb"
            :src="game.thumb"
            alt=""
            loading="lazy"
            class="w-full h-20 object-cover bg-gray-700"
          />
          <div v-else class="w-full h-20 bg-gray-700" />
          <p class="p-2 text-sm font-medium truncate" :title="game.name">{{ game.name }}</p>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
