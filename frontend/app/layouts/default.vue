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

const isSearchPage = computed(() => route.path === '/')

// Top bar search: always on other pages; on / only once the page's own box scrolled away.
// While it has focus it stays, so focus is never dropped onto <body> mid-typing.
const pageSearchVisible = usePageSearchVisible()
const quickFocused = ref(false)
const showQuickSearch = computed(
  () => !isSearchPage.value || !pageSearchVisible.value || quickFocused.value,
)

function onQuickFocusOut(event: FocusEvent) {
  const box = event.currentTarget as HTMLElement
  if (!box.contains(event.relatedTarget as Node | null)) quickFocused.value = false
}
</script>

<template>
  <div class="min-h-screen">
    <!-- Pinned while scrolling. z-30: above page content and the quick search list's own z-20;
         the screenshot full view is a modal <dialog> in the top layer, so it stays above this. -->
    <header class="sticky top-0 z-30 border-b border-line bg-bg/80 backdrop-blur">
      <!-- Phone/tablet: wrapping flex (logo, search, theme in row 1; links + currency in row 2).
           lg+: three columns, the search box in the middle of the bar. -->
      <nav
        class="max-w-screen-2xl mx-auto flex flex-wrap items-center justify-between gap-x-2 sm:gap-x-4 gap-y-2 px-3 py-3 sm:p-4 lg:grid lg:grid-cols-[1fr_auto_1fr]"
      >
        <NuxtLink
          :to="navTo('/')"
          class="flex items-center gap-2 font-display text-lg sm:text-xl font-bold rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent lg:justify-self-start"
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
        <!-- The wrapper always exists (it pushes the theme button right on phones); the box
             fades in on / once the page's own search box is out of view -->
        <div
          class="ml-auto lg:ml-0 lg:justify-self-center"
          @focusin="quickFocused = true"
          @focusout="onQuickFocusOut"
        >
          <Transition
            enter-active-class="transition duration-150 ease-out"
            enter-from-class="opacity-0 translate-y-1 scale-[0.98]"
            leave-active-class="transition duration-100 ease-in"
            leave-to-class="opacity-0 translate-y-1 scale-[0.98]"
          >
            <QuickSearch v-if="showQuickSearch" :icon-until-lg="isSearchPage" />
          </Transition>
        </div>
        <!-- display: contents below lg, so theme (row 1) and links (row 2) stay separate flex
             items and a phone keeps two rows; lg+: one right-aligned group -->
        <div class="contents lg:flex lg:items-center lg:justify-self-end lg:gap-4">
        <!-- Theme presets sit in the first row (next to the logo) so the phone layout stays two rows -->
        <ThemeSwitcher />
        <!-- Links and currency share one row, so a phone gets two rows in all -->
        <div class="flex flex-wrap lg:flex-nowrap items-center justify-end gap-1.5 sm:gap-4">
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
        </div>
      </nav>
    </header>

    <!-- The search page uses the full width; other pages keep a readable width -->
    <main class="mx-auto p-6" :class="isSearchPage ? 'max-w-screen-2xl' : 'max-w-6xl'">
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
