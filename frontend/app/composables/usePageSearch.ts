// Whether the search page's own search box is on screen. The search page (pages/index.vue)
// observes its box and sets this; the top bar shows its search box on / only while it is false.
// Starts true so the top bar box does not flash in before the page's observer reports.
export function usePageSearchVisible() {
  return useState('page-search-visible', () => true)
}
