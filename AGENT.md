# AGENT.md

Instructions for AI coding agents (Claude Code and others) working on this repo.

## Role

Help the owner implement and develop the **game-price-compare-web** website: a game price search
(CheapShark + exchange rates) with a game detail page (IGDB info + every store's price).

- `frontend/`: Nuxt 4 (Vue 3, TypeScript) + Tailwind, `ssr: false`, prerendered with `nuxt generate`
- `backend/`: Flask API (`/api/search`, `/api/games/<id>`, `/api/health`)
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
- Tailwind for styling; handle loading, empty and error states on every data-driven view.

## Checks before saying "done"

```bash
cd backend && pytest
cd frontend && npm run type-check && npm run lint
```

For UI changes also run the app (`FLASK_DEBUG=1 python app.py` + `npm run dev`) and check the page
in the browser. Report results honestly: if a check fails or was skipped, say so.
Update `README.md` when env vars, endpoints, folder layout or run/deploy steps change.
