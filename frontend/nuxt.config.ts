// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',

  // Every page is prerendered to static HTML by `nuxt generate` (see vercel.json buildCommand),
  // so nothing in Nuxt runs on a server in production. Search runs in the browser and calls
  // /api/*, which Vercel rewrites to the Flask service.
  // SSR is only used at build time here. Do not add server-side data fetching without a
  // service binding (relative /api URLs do not work on the server).
  ssr: true,

  routeRules: {
    // The search page is client-only: with SSR HTML, text typed before Vue hydrates is wiped
    // when v-model takes over. Its HTML is just the app shell; /about stays fully prerendered.
    '/': { ssr: false },
    // Listed explicitly: the prerender crawler starts at / and finds no links in an SPA shell
    '/about': { prerender: true },
    // Prerendered shell; the list itself is read from localStorage in the browser (<ClientOnly>)
    '/wishlist': { prerender: true },
    '/alerts': { prerender: true },
    '/browse': { prerender: true },
    // Client-only: game ids are dynamic, so these pages cannot be prerendered. A direct visit
    // gets the SPA shell (200.html), see the /games route in vercel.json.
    '/games/**': { ssr: false },
  },

  devtools: { enabled: true },

  modules: ['@nuxtjs/tailwindcss'],
  tailwindcss: {
    cssPath: '~/assets/css/main.css',
  },

  app: {
    head: {
      title: 'Game Price Compare',
      link: [{ rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }],
    },
  },

  nitro: {
    // Local dev only: forward /api/* to Flask, like Vite's server.proxy did before.
    // In production vercel.json rewrites /api/* to the api service instead.
    devProxy: {
      '/api': {
        target: `${process.env.API_PROXY_TARGET ?? 'http://localhost:5000'}/api`,
        changeOrigin: true,
      },
    },
  },
})
