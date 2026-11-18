import type { Ref } from 'vue'

// Snap between the search page hero and the content below it (layout-04). Only the
// hero/content boundary snaps: one scroll down on the hero glides to the content, one scroll up
// at the content top glides back to the hero, and the page never rests in between. Inside the
// content scrolling is normal. CSS scroll-snap is not used: with a content area much taller than
// the screen it can stop halfway or need several scrolls to leave it.

// Wheel events closer together than this belong to one gesture (touchpad momentum included)
const GESTURE_GAP_MS = 200
// Finger travel before a swipe counts as a scroll
const SWIPE_PX = 10
// Unlock even if `scrollend` never fires (old browser, scroll already at the target)
const UNLOCK_FALLBACK_MS = 1000
// Scroll positions this close count as "at" a snap point
const EPSILON = 2

const DOWN_KEYS = new Set(['PageDown', 'ArrowDown', ' '])
const UP_KEYS = new Set(['PageUp', 'ArrowUp', 'Home'])

export function useHeroSnap(options: {
  enabled: Ref<boolean>
  hero: Ref<HTMLElement | null>
  content: Ref<HTMLElement | null>
}) {
  const { enabled, hero, content } = options

  let busy = false // a snap glide is running
  let snapGesture = false // the current wheel/touch gesture already snapped: swallow the rest
  let lastWheel = 0
  let touchY: number | null = null
  let swipeDir = 0 // last touch swipe direction since the last settle (1 down, -1 up, 0 none)
  let unlockTimer: ReturnType<typeof setTimeout> | undefined
  let settleTimer: ReturnType<typeof setTimeout> | undefined

  /** Scroll position that shows the content under the top bar (honours its scroll-margin-top) */
  function contentTop(): number {
    const el = content.value!
    const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0
    return Math.max(0, Math.round(el.getBoundingClientRect().top + window.scrollY - margin))
  }

  /** Snapping is on: hero shown and it fits the window (else part of it would be unreachable) */
  function active(): boolean {
    if (!enabled.value || !hero.value || !content.value) return false
    const bar = document.querySelector('header')?.offsetHeight ?? 0
    return hero.value.offsetHeight + bar <= window.innerHeight + EPSILON
  }

  function reducedMotion() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  function unlock() {
    clearTimeout(unlockTimer)
    busy = false
  }

  function scrollToY(top: number) {
    if (Math.abs(window.scrollY - top) < EPSILON) return
    busy = true
    clearTimeout(unlockTimer)
    unlockTimer = setTimeout(unlock, UNLOCK_FALLBACK_MS)
    window.scrollTo({ top, behavior: reducedMotion() ? 'auto' : 'smooth' })
  }

  /** Glide to the hero top or to the content (also used by the hero's down arrow) */
  function go(target: 'hero' | 'content') {
    if (!content.value) return
    scrollToY(target === 'hero' ? 0 : contentTop())
  }

  /**
   * What a scroll in `dir` (1 down, -1 up) of about `delta` px does at the current position:
   * 'content' / 'hero' = snap there, 'clamp' = stop exactly at the content top (a scroll up from
   * just below it would otherwise end inside the hero), null = scroll normally.
   */
  function decide(dir: number, delta: number): 'content' | 'hero' | 'clamp' | null {
    const y = window.scrollY
    const ct = contentTop()
    if (dir > 0 && y < ct - EPSILON) return 'content'
    if (dir < 0 && y > 0 && y <= ct + EPSILON) return 'hero'
    if (dir < 0 && y > ct && y - delta < ct) return 'clamp'
    return null
  }

  function apply(action: 'content' | 'hero' | 'clamp') {
    if (action === 'clamp') scrollToY(contentTop())
    else go(action)
  }

  /** The event happened inside something that scrolls itself in that direction (a dropdown list) */
  function scrollsItself(target: EventTarget | null, dir: number): boolean {
    let el = target instanceof Element ? target : null
    while (el && el !== document.body && el !== document.documentElement) {
      const { overflowY } = getComputedStyle(el)
      if ((overflowY === 'auto' || overflowY === 'scroll') && el.scrollHeight > el.clientHeight) {
        const canScroll =
          dir > 0 ? el.scrollTop + el.clientHeight < el.scrollHeight - 1 : el.scrollTop > 0
        if (canScroll) return true
      }
      el = el.parentElement
    }
    return false
  }

  function onWheel(event: WheelEvent) {
    if (!active() || event.ctrlKey || event.deltaY === 0) return
    const dir = Math.sign(event.deltaY)
    if (scrollsItself(event.target, dir)) return

    const now = performance.now()
    const newGesture = now - lastWheel > GESTURE_GAP_MS
    lastWheel = now
    // Mid-glide, or momentum from a gesture that already snapped: swallow it (no double jump)
    if (busy || (snapGesture && !newGesture)) {
      event.preventDefault()
      return
    }
    snapGesture = false

    // deltaMode 1 = lines, 2 = pages; turn into px for the clamp check
    const px = Math.abs(event.deltaY) * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? window.innerHeight : 1)
    const action = decide(dir, px)
    if (!action) return
    event.preventDefault()
    snapGesture = true
    apply(action)
  }

  function onTouchStart(event: TouchEvent) {
    touchY = event.touches.length === 1 ? event.touches[0]!.clientY : null
    snapGesture = false
  }

  function onTouchMove(event: TouchEvent) {
    if (touchY === null || !active()) return
    if (busy || snapGesture) {
      if (event.cancelable) event.preventDefault()
      return
    }
    const moved = touchY - event.touches[0]!.clientY // > 0: finger up = scroll down
    if (Math.abs(moved) < SWIPE_PX) return
    const dir = Math.sign(moved)
    swipeDir = dir
    if (scrollsItself(event.target, dir)) return
    const action = decide(dir, Math.abs(moved))
    if (!action || !event.cancelable) return
    event.preventDefault()
    snapGesture = true
    apply(action)
  }

  function onTouchEnd() {
    touchY = null
  }

  function onKeydown(event: KeyboardEvent) {
    if (!active() || event.altKey || event.ctrlKey || event.metaKey) return
    // Typing, buttons (Space presses them) and widgets with their own arrow keys keep the key
    const target = event.target as HTMLElement | null
    if (
      target?.closest(
        'input, textarea, select, button, [contenteditable="true"], [role="listbox"], [role="menu"], [role="combobox"], [role="option"]',
      )
    ) {
      return
    }
    const isDown = DOWN_KEYS.has(event.key) && !(event.key === ' ' && event.shiftKey)
    const isUp = UP_KEYS.has(event.key) || (event.key === ' ' && event.shiftKey)
    if (!isDown && !isUp) return
    if (busy) {
      event.preventDefault()
      return
    }
    const action = decide(isDown ? 1 : -1, window.innerHeight)
    if (!action) return
    event.preventDefault()
    apply(action)
  }

  // A scroll that ended between the hero and the content (scrollbar drag, or a swipe the browser
  // had already started scrolling natively, so it could not be cancelled): a swipe finishes in
  // its direction, anything else settles on the closer side. `scrollend` where supported, else
  // a short pause in scroll events.
  function settle() {
    const dir = swipeDir
    swipeDir = 0
    if (busy) {
      unlock()
      return
    }
    if (!active()) return
    const y = window.scrollY
    const ct = contentTop()
    if (y <= EPSILON || y >= ct - EPSILON) return
    if (dir) go(dir > 0 ? 'content' : 'hero')
    else go(y < ct / 2 ? 'hero' : 'content')
  }

  function onScroll() {
    clearTimeout(settleTimer)
    settleTimer = setTimeout(settle, 150)
  }

  const hasScrollEnd = import.meta.client && 'onscrollend' in window

  onMounted(() => {
    window.addEventListener('wheel', onWheel, { passive: false })
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: false })
    window.addEventListener('touchend', onTouchEnd, { passive: true })
    window.addEventListener('keydown', onKeydown)
    if (hasScrollEnd) window.addEventListener('scrollend', settle)
    else window.addEventListener('scroll', onScroll, { passive: true })
  })

  onBeforeUnmount(() => {
    window.removeEventListener('wheel', onWheel)
    window.removeEventListener('touchstart', onTouchStart)
    window.removeEventListener('touchmove', onTouchMove)
    window.removeEventListener('touchend', onTouchEnd)
    window.removeEventListener('keydown', onKeydown)
    window.removeEventListener('scrollend', settle)
    window.removeEventListener('scroll', onScroll)
    clearTimeout(unlockTimer)
    clearTimeout(settleTimer)
  })

  return { go }
}
