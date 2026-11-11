# game-price-compare-web

My first web project by myself

ค้นหาราคาเกมที่ถูกที่สุดจาก [CheapShark](https://www.cheapshark.com/) และแปลงสกุลเงินด้วย [open.er-api.com](https://open.er-api.com/)

- `frontend/`: Nuxt 4 (Vue 3) + Tailwind CSS, prerendered to static HTML
- `backend/`: Flask (`/api/search`, `/api/health`)

```
frontend/
  nuxt.config.ts          # prerender settings, Tailwind, dev proxy /api -> Flask
  app/
    app.vue               # root: <NuxtLayout> + <NuxtPage>, title template
    layouts/default.vue   # header + nav shared by every page
    pages/                # file = route (index.vue -> /, about.vue -> /about)
    components/           # GameCard, CurrencySelect (auto-imported)
    utils/searchGames.ts  # fetch /api/search with abort + 30 s timeout (auto-imported)
    types.ts              # Game, CURRENCIES (matches the /api/search response)
    error.vue             # 404 / error page

backend/
  app.py                  # entrypoint (Vercel loads `app` here)
  game_api/
    __init__.py           # create_app()
    config.py             # URLs, timeouts, cache durations, env vars
    errors.py             # UpstreamError, InvalidCurrencyError
    http.py               # shared GET with timeout + User-Agent
    routes/               # HTTP layer only: read params, call a service, map errors to status codes
      search.py           #   GET /api/search
      health.py           #   GET /api/health
    services/             # business logic + external APIs, no Flask imports
      search.py           #   search_prices(): combine games, stores, exchange rate
      cheapshark.py       #   CheapShark API (games, deal stores, store names cached 1 day)
      exchange.py         #   USD exchange rates (cached 30 min, stale on error)
  tests/                  # one file per layer, external APIs mocked
```

## Run locally

```bash
# Terminal 1: backend (http://localhost:5000)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
FLASK_DEBUG=1 python app.py

# Terminal 2: frontend (http://localhost:3000), needs Node 22.22+ or 24
cd frontend
nvm use          # reads .nvmrc
npm ci
npm run dev
```

The Nuxt dev server proxies `/api/*` to `http://localhost:5000` (`nitro.devProxy` in `frontend/nuxt.config.ts`), so the frontend always calls `/api/...` on its own origin. If Flask is not running, searches fail after 30 s with a timeout message.

Check the production build locally: `npm run generate` writes static files to `frontend/.output/public`.

Or with Docker: `docker compose up --build`

### Tests and checks

```bash
cd backend
pip install -r requirements-dev.txt
pytest

cd ../frontend
npm run type-check
npm run lint
```

### Environment variables (backend)

| Name | Default | Purpose |
|---|---|---|
| `CHEAPSHARK_USER_AGENT` | `PriceCompareApp/1.0` | CheapShark rejects generic User-Agents. Set e.g. `MyApp/1.0 (you@example.com)` |
| `FLASK_DEBUG` | off | `1` enables debug mode. Never on in production |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Local server bind address |

## Deploy (Vercel)

`vercel.json` uses [Vercel Services](https://vercel.com/docs/services) (beta): `frontend/` is built with `nuxt generate` into static HTML (no Node server at runtime) and `backend/` runs as a Python function. `/api/*` goes to Flask, everything else to the frontend, on one domain.

Pages are prerendered at build time, so they must not fetch data on the server. If a page ever needs server-side data from Flask, it needs a Vercel service binding for the API URL, because relative `/api` URLs only work in the browser.

1. Push to GitHub
2. Import the repo on vercel.com (Root Directory: repo root)
3. (Optional) set `CHEAPSHARK_USER_AGENT` in Project Settings → Environment Variables
