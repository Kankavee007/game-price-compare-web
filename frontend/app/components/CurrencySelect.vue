<script setup lang="ts">
import { CURRENCIES, type Currency } from '~/types'

const model = defineModel<Currency>({ required: true })
// compact: smaller box for the top bar showing just the code (USD), so it fits next to the
// nav links on a phone; the open list still shows the full labels with flags
defineProps<{ compact?: boolean }>()

const options = CURRENCIES.map((c) => ({ value: c.code as Currency, label: c.label }))
</script>

<template>
  <PickSelect
    v-model="model"
    :options="options"
    label="Currency"
    :compact="compact"
    :short="compact ? (o) => o.value : undefined"
  />
</template>
