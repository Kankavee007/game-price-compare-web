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
- Theme: use the color tokens only (`bg-bg`, `bg-surface`, `bg-surface-2`, `border-line`, `text-fg`,
  `text-muted`, `text-subtle`, `text-accent`, `bg-accent-strong`, `text-accent-2`, `text-success`,
  `text-warn`, `text-danger`, `bg-danger-strong`), never raw palette classes like `gray-800` or
  `blue-500`: they would break the presets (Nebula / Lime / Ember in `assets/css/main.css`).
  A new preset must keep text at WCAG AA (4.5:1) on `bg`, `surface` and `surface-2`.
- Reuse the shared classes in `main.css`: `.panel`, `.field`, `.btn-primary`, `.btn-ghost`,
  `.nav-link`, `.skeleton`. Loading states use `.skeleton` shapes, not "Loading…" text.
- Motion: `v-reveal` for things that should fade in on first view; keep transitions short
  (≤ 0.5 s). Everything must still show under `prefers-reduced-motion` and without
  IntersectionObserver.
- Popovers (dropdowns, menus) follow `StoreSelect.vue` / `ThemeSwitcher.vue`: keyboard support,
  Esc returns focus to the trigger, close on outside click, stay inside the screen on phones.
- Brand assets live in `public/brand/` (full logo for large areas, mark-only for small ones).
  The source artwork is `pictures/pixsales.png`.

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
