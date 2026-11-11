<template>
  <div class="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 text-white">
    <header class="border-b border-gray-700">
      <nav class="max-w-6xl mx-auto flex items-center justify-between gap-4 p-4">
        <NuxtLink to="/" class="text-xl font-bold">🎮 Game Price Compare</NuxtLink>
        <ul class="flex gap-4 text-gray-300">
          <li>
            <NuxtLink to="/" class="hover:text-white" active-class="text-white font-semibold"
              >Search</NuxtLink
            >
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
  </div>
</template>
