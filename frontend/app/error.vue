<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()
useHead({ title: props.error.statusCode === 404 ? 'Page not found' : 'Error' })
</script>

<template>
  <NuxtLayout>
    <div class="text-center space-y-4 py-16">
      <h1 class="text-3xl font-bold">
        {{ error.statusCode === 404 ? 'Page not found' : 'Something went wrong' }}
      </h1>
      <button class="text-blue-400 hover:underline" @click="clearError({ redirect: '/' })">
        Back to search
      </button>
    </div>
  </NuxtLayout>
</template>
