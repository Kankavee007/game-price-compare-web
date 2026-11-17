// v-reveal: the element fades and rises in the first time it scrolls into view.
// Elements that enter together (a page of results) get a short stagger, capped so a long list
// never waits long. Nothing is hidden when motion is reduced or IntersectionObserver is missing.
export default defineNuxtPlugin((nuxtApp) => {
  let observer: IntersectionObserver | null = null

  if (
    import.meta.client &&
    'IntersectionObserver' in window &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  ) {
    observer = new IntersectionObserver(
      (entries) => {
        let i = 0
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const el = entry.target as HTMLElement
          el.style.setProperty('--reveal-delay', `${Math.min(i++, 8) * 50}ms`)
          el.classList.add('reveal-in')
          observer?.unobserve(el)
        }
      },
      { rootMargin: '0px 0px -5% 0px', threshold: 0.05 },
    )
  }

  nuxtApp.vueApp.directive<HTMLElement>('reveal', {
    mounted(el) {
      if (!observer) return
      el.classList.add('reveal')
      observer.observe(el)
    },
    unmounted(el) {
      observer?.unobserve(el)
    },
  })
})
