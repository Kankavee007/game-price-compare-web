// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2026-11-01',

  // Phase 1: SPA only. The browser calls /api/* and Vercel rewrites it to the Flask service,
  // so nothing in Nuxt runs on the server in production.
  ssr: false,

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
