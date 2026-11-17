<script setup lang="ts">
useHead({
  titleTemplate: (title) => (title ? `${title} - PixSales` : 'PixSales - Pixel Perfect Deals'),
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
