<script setup lang="ts">
import { CURRENCIES, type Currency } from '@/types'

const model = defineModel<Currency>({ required: true })
</script>

<template>
  <select
    v-model="model"
    aria-label="Currency"
    class="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
  >
    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.label }}</option>
  </select>
</template>
