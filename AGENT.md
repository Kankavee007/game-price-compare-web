# AGENT.md

Instructions for AI coding agents (Claude Code and others) working on this repo.

## Role

Help the owner implement and develop the **game-price-compare-web** website (brand: **PixSales -
Pixel Perfect Deals**): a game price search (CheapShark + exchange rates) with a game detail page
(IGDB info + every store's price).

- `frontend/`: Nuxt 4 (Vue 3, TypeScript) + Tailwind, every page prerendered with `nuxt generate`.
  `ssr: true` by default (build-time only), with `routeRules` turning SSR off for `/` and
  `/games/**` (client-only shells). `/about`, `/wishlist`, `/alerts`, `/browse` are SSR-prerendered.
- `backend/`: Flask API under `/api/*` (search, deals, stores, prices, alerts, genres, browse,
  games/<id>, health; full list in README)
- `harness/feature_list.json`: feature specs and progress tracker
- Deploy: Vercel Services (`vercel.json`), local Docker via `docker-compose.yml`

`README.md` has the full folder map, env vars, run and deploy steps. Read it before starting a task.

## Rule 1: Spec before code

Every **new feature** (or a change that alters user-facing behavior) gets a spec in
`harness/feature_list.json` **before** any implementation code is written.

1. Read `harness/feature_list.json` to see existing phases, ids and notes.
2. Add one or more feature entries (format below). Use a new id prefix per feature group
   (e.g. `detail-01`, `detail-02`) and the next `phase` number. Add a line to top-level `notes`
   if the feature needs context (data source, constraints, design decisions).
3. Show the spec to the owner and wait for approval before implementing.
   Committing the spec on its own (`Spec: <feature>`) is preferred, as in past history.
4. Implement one feature entry at a time.
5. Set `"passes": true` **only** after running every step and the workflows and seeing them work
   (tests, type-check, lint, and a manual check in the browser where relevant). Never flip it on
   faith. If something cannot be verified (e.g. needs a Vercel deploy), leave it `false` and say why.

Bug fixes, refactors and small tweaks that keep behavior the same do not need a spec entry.
If unsure whether something counts as a feature, ask.

### Feature entry format

Existing entries only have `steps`. New entries also have `workflows`:

```json
{
  "id": "wishlist-01",
  "phase": 4,
  "category": "functional",
  "description": "User can save a game to a wishlist from the detail page",
  "workflows": {
    "main": [
      "User opens /games/<id> and clicks 'Add to wishlist'",
      "Button changes to 'In wishlist'; game appears on /wishlist with its current cheapest price"
    ],
    "alternate": [
      "Game is already in the wishlist: button shows 'Remove from wishlist' and removes it on click",
      "Wishlist is empty: /wishlist shows an empty state with a link to search"
    ],
    "error": [
      "Price API fails (5xx/timeout): wishlist still lists the game, price shows 'unavailable' with a retry button",
      "Storage unavailable (private mode): show a message that the wishlist cannot be saved, page does not crash"
    ]
  },
  "steps": [
    "Implementation and verification steps, in order, each one checkable",
    "Add backend tests with external APIs mocked; cd backend && pytest stays green",
    "cd frontend && npm run type-check && npm run lint pass",
    "Open the page in the browser and walk through every workflow above"
  ],
  "passes": false
}
```

- `category`: `setup` | `functional` | `devops` | `deploy` | `docs`
- `main`: the happy path, step by step from the user's view.
- `alternate`: valid but different paths (empty results, already-done state, other inputs, other currency...).
- `error`: what goes wrong and what the user sees (upstream API down, timeout, 404, invalid input,
  missing env var/credentials). Every error workflow must name the visible result, never a blank page.
- Keep existing entries unchanged; do not rewrite history of passed features.

## Rule 2: Ask before anything dangerous

**Stop and ask the owner first, and wait for an explicit yes**, before any of these:

- Deleting, moving or overwriting files or folders (`rm`, `mv` over existing files, `git clean`,
  rewriting a file you have not read). Especially any `.env*` file: never delete or replace it.
- Destructive git: `git reset --hard`, `git checkout -- <file>`, `git restore`, `git stash drop`,
  `git push --force`, deleting branches, rewriting commits, amending pushed commits.
- Removing or downgrading dependencies, deleting `node_modules`, `venv`, lock files, `.output`, caches.
- Changing deploy or infra config: `vercel.json`, `docker-compose.yml`, Dockerfiles, Vercel env vars,
  running deploys.
- Anything that sends data outside the machine or is hard to undo (pushing, opening PRs, calling
  paid APIs in a loop).

When asking, say exactly what will be removed or changed and why. Prefer a reversible alternative
(rename to `*.bak`, new branch, comment out) when one exists. Approval for one action does not
cover the next one.

Safe without asking: reading files, creating new files, editing source files for the agreed task
(including deleting lines, functions or code patterns inside a file when the task needs it),
running tests, lint, type-check, dev servers and builds.

### `.env` files

- Allowed: open, read and edit `.env` files (e.g. add a new variable the task needs).
- Never print or repeat secret values: not in replies, commit messages, PR text, logs, test output,
  docs or requests to external services. Refer to a variable by name only (`TWITCH_CLIENT_SECRET is set`).
- Avoid shell commands that dump the file to output (`cat .env`, `env`, `printenv`); check a single
  variable with something that hides the value, e.g. `grep -c '^TWITCH_CLIENT_ID=.' backend/.env`.
- Never commit `.env` or copy real values into `.env.example`.

## Git

- Commit or push only when asked. Never commit on `main` directly; create a branch
  (e.g. `feature/wishlist`, `fix/search-timeout`) and open a PR.
- Never commit secrets (`.env`, API keys, Twitch credentials).
- Clear commit messages in English, imperative mood (e.g. `Add wishlist API endpoint`).

## Code conventions

Backend (`backend/game_api/`):
- `routes/` is the HTTP layer only: read params, call a service, map errors to status codes.
- `services/` holds business logic and external API calls, no Flask imports.
- Use `http.py` for outbound requests (timeout + User-Agent) and errors from `errors.py`.
- Config and env vars live in `config.py`. Credentials stay on the server, never sent to the browser.
- Every new service/route gets tests in `backend/tests/` with external APIs mocked.

Frontend (`frontend/app/`):
- Pages in `pages/` (file = route), shared UI in `components/`, API calls in `utils/` via `apiGet`.
- Keep `types.ts` matching the API responses.
- Pages are prerendered: no server-side data fetching. Dynamic routes need `routeRules` +
  a `vercel.json` route (see README "Deploy").
- Browser-only state (localStorage, `<html data-theme>`, `window`) must be read on the client
  (`onMounted`, `<ClientOnly>`). On SSR-prerendered routes `useState` arrives with the server's
  value, so sync it after mount (see `useTheme().sync()`).
- Tailwind for styling; handle loading, empty and error states on every data-driven view.
- Styling, theme, motion, brand and UI components: follow **Design system** below.

## Design system

Every new page or component must look like it was always part of PixSales. Before building UI,
open a similar existing view (`GameCard.vue`, `SearchFilters.vue`, `StoreSelect.vue`,
`pages/games/[id].vue`) and copy its patterns instead of inventing new ones.

### Look and feel

- Clean and modern with a playful touch, but never loud: dark backgrounds, soft glass panels,
  one accent color doing the work, small rewarding hover moments (lift + glow).
- Dark only. Every preset is a dark theme; there is no light mode.
- Content first: game art is the most colorful thing on the page, the UI stays calm around it.

### Brand

- Name: **PixSales**, tagline **Pixel Perfect Deals** (title case, or spaced uppercase under the
  logo). Tab titles: `<page> - PixSales`; home: `PixSales - Pixel Perfect Deals`.
- Source artwork: `pictures/pixsales.png` (white "Pix" + green "Sales" on transparent).
  Web versions in `frontend/public/brand/`:
  - `pixsales-logo.png`: full logo, for large areas only (search hero, about, error page) via
    `<BrandLogo />`.
  - `pixsales-mark.png`: the cropped "P" controller mark without text, for small areas (top bar,
    favicon, touch icon). In the top bar it sits next to the text `Pix<span class="text-brand">Sales</span>`.
  - Regenerate both from the source artwork (crop, never redraw); keep transparent backgrounds.
- `text-brand` / `--c-brand` (logo green `56 238 87`) is the same in every preset and is only for
  the brand name and logo accents, not for UI states.

### Color

- Colors are CSS variables in `app/assets/css/main.css` holding `R G B` channels, mapped to
  Tailwind names in `tailwind.config.js`. Use only these tokens, never raw palette classes
  (`gray-800`, `blue-500`...) or hex values in components; `text-white` only on `accent-strong`
  and `danger-strong` fills:

  | Token | Use |
  |---|---|
  | `bg` | page background (with the fixed radial glows on `body`) |
  | `surface` / `surface-2` | panels, cards / inputs, hovered or raised areas |
  | `line` / `line-strong` | borders / hovered borders |
  | `fg` / `muted` / `subtle` | main text / secondary text / hints and placeholders |
  | `accent` | links, focus rings, current item, highlights |
  | `accent-strong` | filled buttons and selected chips (white text on it) |
  | `accent-2` | second highlight (genre name, small emphasis) |
  | `success` | prices and "cheapest" states |
  | `warn` / `danger` / `danger-strong` | lowest-ever badges / error text / filled red badges |

- Opacity modifiers are fine (`bg-surface/70`, `border-danger/40`).
- Presets: Nebula (default, `:root`), Lime and Ember (`:root[data-theme=...]`). A new preset
  redefines every variable, stays dark, and keeps `fg`, `muted`, `subtle`, `accent`, `accent-2`,
  `success`, `warn`, `danger` at WCAG AA (4.5:1) on `bg`, `surface` and `surface-2`, with white
  text at 4.5:1 on `accent-strong` and `danger-strong`. Add it to `THEMES` in
  `composables/useTheme.ts` and to the inline script in `nuxt.config.ts`.

### Type

- Body: Inter (`font-sans`). Headings `h1`-`h3`: Space Grotesk (`font-display`, tight tracking,
  set globally). Prices in cards use `font-display font-bold`.
- Sizes: page title `text-3xl font-bold`, section title `text-xl font-semibold`, body
  `text-base`, controls and secondary text `text-sm`, captions `text-xs`.

### Shape, surfaces, spacing

- Radius: `rounded-xl` for controls and small boxes, `rounded-2xl` for cards, panels and popovers,
  `rounded-full` for chips and badges.
- Shared classes (in `main.css`), use them before writing long class lists:
  `.panel` (glass card), `.field` (input / dropdown button), `.btn-primary` (gradient filled
  action), `.btn-ghost` (outlined action; add `border-danger/60 hover:text-danger` for retry
  buttons), `.nav-link` / `.nav-link-active`, `.skeleton` (loading shape).
- Controls are 40px high (`h-10`) with labels above in `text-sm text-muted`; filter rows use an
  equal-column grid (1 / 2 / 4 columns).
- Page width `max-w-6xl`, page padding `p-6`, sections `space-y-8` / `mb-10`, grids `gap-4`–`gap-6`.
- Elevation: cards lift on hover (`hover:-translate-y-1` / `-1.5`) with `shadow-glow` and an
  accent ring or border; popovers use `bg-surface/95 backdrop-blur border-line shadow-2xl`.

### Motion

- Short and soft: hovers 150–300 ms, popovers 100–150 ms (fade + 1px rise + 98% scale), page
  change 220 ms (`.page-*`), reveal 500 ms.
- `v-reveal` on cards, rows and sections that should fade in on first view (put it on an outer
  wrapper if the element has its own hover transform). Images fade in on load (`GameImage`).
- Everything must render fully under `prefers-reduced-motion` and without IntersectionObserver.

### Components to reuse

- Dropdown, single choice: `PickSelect`. Multiple choice with search: `StoreSelect`.
  Action menu: `ThemeSwitcher` pattern. Never use a native `<select>`.
- All popovers: keyboard support, Esc returns focus to the trigger, close on outside click or
  Tab away, open toward the side with room so they stay inside a 360px screen, `z-20`–`z-40`
  (the top bar is `z-30`).
- Game tiles: `GameCard` (+ `GameImage` for covers with fallback). Logo: `BrandLogo`.
- States: loading = `.skeleton` shapes of the real content; empty = short text + a link to act;
  error = `⚠️` + message in `text-danger` + a "Try again" `.btn-ghost` when retry makes sense.

### Copy and icons

- Short, friendly, plain English ("No store matches", "Try again"). Sentence case for buttons
  and labels.
- Emoji are the icon set (🔥 🎨 ♡ 🏷️ ⚠️ 💰 🎮); mark decorative ones `aria-hidden`.

### Layout and accessibility checks

- Works from 360px wide with no sideways scroll; the sticky top bar stays two rows on phones
  (at 320px a third row is acceptable).
- Every control has a visible `focus-visible` ring in `accent` and an accessible name.
- Check new UI in all three presets (`localStorage.theme = 'lime'`, `'ember'`) and at 360px,
  768px and desktop before calling it done.

## Checks before saying "done"

```bash
cd backend && pytest
cd frontend && npm run type-check && npm run lint
```

For UI changes also run the app (`FLASK_DEBUG=1 python app.py` + `npm run dev`) and check the page
in the browser at phone (360px) and desktop widths. Report results honestly: if a check fails or
was skipped, say so.

- CheapShark rate-limits quickly (HTTP 429, shown as "price service unavailable"). Each search page
  load makes 4+ requests, so do not reload data pages in a loop while testing; wait a few minutes
  and test pages one at a time. Static pages (`/about`, `/alerts`) need no API.
- Changing `tailwind.config.js` needs a dev server restart.

Update `README.md` when env vars, endpoints, folder layout or run/deploy steps change.
