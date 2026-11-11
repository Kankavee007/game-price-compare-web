<script setup lang="ts">
useHead({ title: 'About' })
</script>

<template>
  <article class="max-w-2xl mx-auto space-y-4 text-gray-300">
    <h1 class="text-3xl font-bold text-white">About</h1>
    <p>
      Game Price Compare finds the cheapest current deal for a game across PC stores and shows the
      price in your currency.
    </p>

    <h2 class="text-xl font-semibold text-white pt-2">Where the data comes from</h2>
    <ul class="list-disc pl-6 space-y-2">
      <li>
        Prices and stores:
        <a
          href="https://www.cheapshark.com/"
          target="_blank"
          rel="noopener noreferrer"
          class="text-blue-400 hover:underline"
          >CheapShark</a
        >
        (prices in USD).
      </li>
      <li>
        Exchange rates:
        <a
          href="https://open.er-api.com/"
          target="_blank"
          rel="noopener noreferrer"
          class="text-blue-400 hover:underline"
          >open.er-api.com</a
        >, refreshed every 30 minutes.
      </li>
    </ul>

    <p class="text-sm text-gray-400">
      Converted prices are estimates. The store page always shows the final price.
    </p>
  </article>
</template>
