<script setup lang="ts">
import { toCurrency, type Currency } from '~/types'

const wishlist = useWishlist()
const route = useRoute()
const router = useRouter()

// One currency for the whole site, kept in the URL (?currency=THB) so links and reloads keep it.
// Pages read it from route.query themselves.
const currency = computed<Currency>({
  get: () => toCurrency(route.query.currency),
  set: (value) => router.replace({ query: { ...route.query, currency: value } }),
})

/** Nav link that keeps the chosen currency (USD is the default, so it is left out) */
function navTo(path: string) {
  return currency.value === 'USD' ? path : { path, query: { currency: currency.value } }
}
</script>

<template>
  <div class="min-h-screen">
    <!-- Pinned while scrolling. z-30: above page content and the quick search list's own z-20;
         the screenshot full view is a modal <dialog> in the top layer, so it stays above this. -->
    <header class="sticky top-0 z-30 border-b border-line bg-bg/80 backdrop-blur">
      <nav
        class="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-x-2 sm:gap-x-4 gap-y-2 px-3 py-3 sm:p-4"
      >
        <NuxtLink
          :to="navTo('/')"
          class="flex items-center gap-2 font-display text-lg sm:text-xl font-bold rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <!-- Small area: the cropped mark only (public/brand/pixsales-mark.png); the name is text -->
          <img
            src="/brand/pixsales-mark.png"
            alt=""
            width="36"
            height="36"
            class="w-8 h-8 sm:w-9 sm:h-9 -my-1"
          />
          <span>Pix<span class="text-brand">Sales</span></span>
        </NuxtLink>
        <!-- The search page has its own search box -->
        <QuickSearch v-if="route.path !== '/'" class="ml-auto" />
        <!-- Theme presets sit in the first row (next to the logo) so the phone layout stays two rows -->
        <ThemeSwitcher :class="{ 'ml-auto': route.path === '/' }" />
        <!-- Links and currency share one row, so a phone gets two rows in all -->
        <div class="flex flex-wrap items-center justify-end gap-1.5 sm:gap-4">
          <ul class="flex items-center sm:gap-1 text-muted">
            <li>
              <NuxtLink :to="navTo('/')" class="nav-link" active-class="nav-link-active"
                >Search</NuxtLink
              >
            </li>
            <li>
              <NuxtLink :to="navTo('/browse')" class="nav-link" active-class="nav-link-active"
                >Browse</NuxtLink
              >
            </li>
            <li>
              <NuxtLink :to="navTo('/wishlist')" class="nav-link" active-class="nav-link-active">
                Wishlist<ClientOnly
                  ><span
                    v-if="wishlist.count.value"
                    class="ml-1 text-xs bg-danger-strong rounded-full px-1.5 py-0.5"
                    >{{ wishlist.count.value }}</span
                  ></ClientOnly
                >
              </NuxtLink>
            </li>
            <li>
              <NuxtLink :to="navTo('/about')" class="nav-link" active-class="nav-link-active"
                >About</NuxtLink
              >
            </li>
          </ul>
          <CurrencySelect v-model="currency" compact />
        </div>
      </nav>
    </header>

    <main class="max-w-6xl mx-auto p-6">
      <slot />
    </main>

    <!-- Wishlist problems (storage blocked or full) from any page -->
    <div
      v-if="wishlist.error.value"
      role="alert"
      class="fixed bottom-4 inset-x-4 sm:left-auto sm:right-4 sm:max-w-sm flex items-start gap-3 p-4 rounded-xl bg-surface/95 backdrop-blur border border-danger shadow-lg"
    >
      <p class="flex-1 text-sm">⚠️ {{ wishlist.error.value }}</p>
      <button
        type="button"
        class="text-muted hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded"
        aria-label="Dismiss"
        @click="wishlist.clearError()"
      >
        ✕
      </button>
    </div>
  </div>
</template>
