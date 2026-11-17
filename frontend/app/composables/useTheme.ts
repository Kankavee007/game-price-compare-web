// Color presets. The colors themselves live in assets/css/main.css under :root[data-theme=...];
// Nebula is the default (no data-theme). An inline script in nuxt.config.ts applies the saved
// preset before the first paint.
export const THEMES = [
  { id: 'nebula', label: 'Nebula', swatches: ['#0a0b18', '#7c3aed', '#22d3ee'] },
  { id: 'lime', label: 'Lime', swatches: ['#0c0d0c', '#a3e635', '#2dd4bf'] },
  { id: 'ember', label: 'Ember', swatches: ['#140e0c', '#fb9278', '#fbbf24'] },
] as const

export type ThemeId = (typeof THEMES)[number]['id']

const KEY = 'theme'
const DEFAULT: ThemeId = 'nebula'

function isTheme(value: unknown): value is ThemeId {
  return THEMES.some((t) => t.id === value)
}

export function useTheme() {
  // Shared by every component. Prerendered pages (ssr: true routes like /about) bring the
  // server's value (always the default), so sync() reads what the inline script applied.
  const current = useState<ThemeId>('theme', () => DEFAULT)

  function sync() {
    const applied = document.documentElement.dataset.theme
    current.value = isTheme(applied) ? applied : DEFAULT
  }

  function set(id: ThemeId) {
    if (id === current.value) return
    const root = document.documentElement
    root.classList.add('theme-switching')
    if (id === DEFAULT) delete root.dataset.theme
    else root.dataset.theme = id
    current.value = id
    window.setTimeout(() => root.classList.remove('theme-switching'), 400)
    // Storage can be blocked (private mode): the preset then lasts for this visit only
    try {
      localStorage.setItem(KEY, id)
    } catch {
      /* not saved */
    }
  }

  return { current, set, sync }
}
