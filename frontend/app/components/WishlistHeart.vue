<script setup lang="ts">
// Heart toggle for game cards. It sits next to the card link, not inside it: a button inside
// an <a> is invalid HTML, and a click on it would also open the game page.
const props = defineProps<{ game: { gameID: string; name: string; thumb: string | null } }>()

const wishlist = useWishlist()
const saved = computed(() => wishlist.has(props.game.gameID))
</script>

<template>
  <button
    type="button"
    class="w-9 h-9 flex items-center justify-center rounded-full bg-black/70 hover:bg-black/90 text-lg leading-none focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    :aria-pressed="saved"
    :aria-label="saved ? `Remove ${game.name} from wishlist` : `Add ${game.name} to wishlist`"
    :title="saved ? 'Remove from wishlist' : 'Add to wishlist'"
    @click="wishlist.toggle(game)"
  >
    <span :class="saved ? 'text-red-500' : 'text-white'" aria-hidden="true">{{
      saved ? '♥' : '♡'
    }}</span>
  </button>
</template>
