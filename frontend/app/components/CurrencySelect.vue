<script setup lang="ts">
import { CURRENCIES, type Currency } from '~/types'

const model = defineModel<Currency>({ required: true })
// compact: smaller box for the top bar, so it fits next to the nav links on a phone
defineProps<{ compact?: boolean }>()
</script>

<template>
  <select
    v-model="model"
    aria-label="Currency"
    class="field"
    :class="compact ? 'px-2 py-1 text-sm' : 'px-4 py-2'"
  >
    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">
      {{ compact ? c.code : c.label }}
    </option>
  </select>
</template>
