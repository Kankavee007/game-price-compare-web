/** @type {import('tailwindcss').Config} */
// @nuxtjs/tailwindcss already scans app/ (pages, components, layouts, app.vue),
// so `content` only needs extra paths outside the Nuxt folders.

// Theme colors are CSS variables (app/assets/css/main.css) holding "R G B" channels, so a
// preset only swaps the variables and opacity modifiers like bg-surface/60 still work.
const token = (name) => `rgb(var(--c-${name}) / <alpha-value>)`

export default {
  content: [],
  theme: {
    extend: {
      colors: {
        bg: token('bg'), // page background
        surface: token('surface'), // cards, panels
        'surface-2': token('surface-2'), // inputs, raised or hovered surfaces
        line: token('line'), // borders
        'line-strong': token('line-strong'),
        fg: token('fg'), // main text
        muted: token('muted'), // secondary text
        subtle: token('subtle'), // hints, placeholders (still AA on every surface)
        accent: token('accent'), // links, focus rings, highlights
        'accent-strong': token('accent-strong'), // filled buttons (white text on it)
        'accent-2': token('accent-2'), // second highlight color
        success: token('success'),
        warn: token('warn'),
        danger: token('danger'), // error text
        'danger-strong': token('danger-strong'), // filled red badges and buttons
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 8px 30px -8px rgb(var(--c-accent) / 0.45)',
      },
    },
  },
  plugins: [],
}
