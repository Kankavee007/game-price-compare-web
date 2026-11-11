<script setup lang="ts">
// Temporary page for nuxt-01..03. The real search page replaces this in nuxt-06.
const { data: health, error } = await useFetch<{ status: string }>('/api/health')
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white p-6">
    <main class="max-w-6xl mx-auto text-center">
      <h1 class="text-3xl font-bold">🎮 Game Price Compare</h1>
      <p class="mt-4 text-gray-400">Nuxt is running. The search page moves here in nuxt-06.</p>
      <p class="mt-2" role="status">
        API:
        <span v-if="health" class="text-green-400 font-semibold">{{ health.status }}</span>
        <span v-else-if="error" class="text-red-400 font-semibold">unreachable</span>
        <span v-else class="text-gray-400">checking…</span>
      </p>
    </main>
  </div>
</template>
