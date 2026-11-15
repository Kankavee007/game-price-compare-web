<script setup lang="ts">
const wishlist = useWishlist()
const route = useRoute()
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
    <header class="border-b border-gray-700">
      <nav class="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-x-4 gap-y-2 p-4">
        <NuxtLink to="/" class="text-xl font-bold">🎮 Game Price Compare</NuxtLink>
        <!-- The search page has its own search box -->
        <QuickSearch v-if="route.path !== '/'" class="ml-auto" />
        <ul class="flex items-center gap-4 text-gray-300">
          <li>
            <NuxtLink to="/" class="hover:text-white" active-class="text-white font-semibold"
              >Search</NuxtLink
            >
          </li>
          <li>
            <NuxtLink
              to="/wishlist"
              class="hover:text-white"
              active-class="text-white font-semibold"
            >
              Wishlist<ClientOnly
                ><span
                  v-if="wishlist.count.value"
                  class="ml-1 text-xs bg-red-600 text-white rounded-full px-1.5 py-0.5"
                  >{{ wishlist.count.value }}</span
                ></ClientOnly
              >
            </NuxtLink>
          </li>
          <li>
            <NuxtLink to="/about" class="hover:text-white" active-class="text-white font-semibold"
              >About</NuxtLink
            >
          </li>
        </ul>
      </nav>
    </header>

    <main class="max-w-6xl mx-auto p-6">
      <slot />
    </main>

    <!-- Wishlist problems (storage blocked or full) from any page -->
    <div
      v-if="wishlist.error.value"
      role="alert"
      class="fixed bottom-4 inset-x-4 sm:left-auto sm:right-4 sm:max-w-sm flex items-start gap-3 p-4 rounded-xl bg-red-900/95 border border-red-500 shadow-lg"
    >
      <p class="flex-1 text-sm">⚠️ {{ wishlist.error.value }}</p>
      <button
        type="button"
        class="text-red-200 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        aria-label="Dismiss"
        @click="wishlist.clearError()"
      >
        ✕
      </button>
    </div>
  </div>
</template>
