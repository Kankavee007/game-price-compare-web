# game-price-compare-web

My first web project by myself

ค้นหาราคาเกมที่ถูกที่สุดจาก [CheapShark](https://www.cheapshark.com/) และแปลงสกุลเงินด้วย [open.er-api.com](https://open.er-api.com/) หน้ารายละเอียดเกมแสดงข้อมูลเกม (ประเภท คะแนน ปก) จาก [IGDB](https://www.igdb.com/) และราคาทุกร้านเรียงจากถูกไปแพง

- `frontend/`: Nuxt 4 (Vue 3) + Tailwind CSS, prerendered to static HTML
- `backend/`: Flask (`/api/search`, `/api/deals`, `/api/stores`, `/api/prices`, `POST /api/alerts`, `POST /api/alerts/manage`, `/api/genres`, `/api/browse`, `/api/games/<id>`, `/api/health`)

```
frontend/
  nuxt.config.ts          # prerender settings, Tailwind, Google Fonts (Inter, Space Grotesk), dev proxy /api -> Flask
  tailwind.config.js      # theme colors as tokens (bg-surface, text-accent...) read from CSS variables
  app/
    app.vue               # root: <NuxtLayout> + <NuxtPage>, title template
    assets/css/main.css   # theme: color variables (Nebula preset), .panel / .field / .btn-* / .nav-link classes
    layouts/default.vue   # sticky header: nav + site-wide currency select (?currency= in the URL)
    pages/                # file = route (index.vue -> /, about.vue -> /about, wishlist.vue -> /wishlist, alerts.vue -> /alerts, browse.vue -> /browse?genre=<id>, games/[id].vue -> /games/<id>)
    components/           # GameCard, CurrencySelect, SearchFilters, GameSection, DiscountSidebar, LowestBadge, WishlistHeart, WishlistSaleNotice, RecentlyViewed, PriceAlertForm, QuickSearch, GameImage (portrait cover with landscape fallback), ScreenshotGallery (auto-imported)
    composables/          # useWishlist, useRecentlyViewed (localStorage, synced across tabs), storedList helper
    utils/                # auto-imported
      apiGet.ts           #   apiGet / apiPost: fetch /api/* with abort + 30 s timeout, ApiError(status)
      searchGames.ts      #   GET /api/search
      listDeals.ts        #   GET /api/deals (search page results with filters)
      getStores.ts        #   GET /api/stores
      getPrices.ts        #   GET /api/prices (wishlist prices)
      setPriceAlert.ts    #   POST /api/alerts (email price alert, email in the body only)
      getGenres.ts        #   GET /api/genres
      browseGenre.ts      #   GET /api/browse (popular games of a genre)
      manageAlerts.ts     #   POST /api/alerts/manage (CheapShark emails a link to manage alerts)
      dealFilters.ts      #   search filters <-> URL query (?min=&max=&sort=&stores=&sale=&rating=)
      getGameDetail.ts    #   GET /api/games/<id>
    types.ts              # Game, GameDetail, DealResult, Store, DealFilters, CURRENCIES (match the API responses)
    error.vue             # 404 / error page

backend/
  app.py                  # entrypoint (Vercel loads `app` here)
  game_api/
    __init__.py           # create_app()
    config.py             # URLs, timeouts, cache durations, env vars
    errors.py             # UpstreamError (+ UpstreamNotFoundError), ConfigError, InvalidCurrencyError, InvalidParamError
    http.py               # shared GET/POST with timeout + User-Agent
    routes/               # HTTP layer only: read params, call a service, map errors to status codes
      search.py           #   GET /api/search
      deals.py            #   GET /api/deals?q=&currency=&minPrice=&maxPrice=&sort=&page=&stores=&onSale=&minRating=
      stores.py           #   GET /api/stores (active stores with logo)
      prices.py           #   GET /api/prices?ids=1,2&currency= (cheapest deal of up to 50 games, for the wishlist)
      alerts.py           #   POST /api/alerts {email, gameID, price, currency} (CheapShark email alert; never logs the email)
                          #   POST /api/alerts/manage {email} (CheapShark emails a link to manage alerts)
      browse.py           #   GET /api/genres (IGDB, cached 1 day), GET /api/browse?genre=12&currency= (popular games of a genre, cached 6 h)
      games.py            #   GET /api/games/<id>
      health.py           #   GET /api/health
    services/             # business logic + external APIs, no Flask imports
      search.py           #   search_prices(): combine games, stores, exchange rate
      deals.py            #   find_deals(): filters, sort, paging, one row per game (cheapest store)
      lowest.py           #   lowest_price_fields(): lowest price ever + isHistoricalLow (compared in USD)
      stores.py           #   list_active_stores(): for the store filter, sorted by name
      prices.py           #   get_prices(): cheapest deal per game for many ids
      alerts.py           #   set_alert(), manage_alerts(): validate, convert price to USD, per IP per hour: 10 alerts, 5 manage emails (in memory)
      browse.py           #   get_genres(), browse(): IGDB popular PC games + CheapShark price by Steam app id (4 lookups at a time)
      game_detail.py      #   get_game_detail(): CheapShark deals + IGDB info (similar games, screenshots), sorted cheapest first
      steam.py            #   steam_cover_url(): portrait Steam cover (library_600x900) from a Steam app id, no API call
      cheapshark.py       #   CheapShark API (search, one game, many games, /deals cached 15 min, store list cached 1 day, price alerts)
      igdb.py             #   IGDB API (Twitch app token cached in memory, match by Steam id then title, genres, popular games)
      exchange.py         #   USD exchange rates (cached 30 min, stale on error)
  tests/                  # one file per layer, external APIs mocked
```

## Run locally

```bash
# Terminal 1: backend (http://localhost:5000)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt   # includes python-dotenv, which loads backend/.env
cp .env.example .env                 # then fill in the Twitch keys (see below)
FLASK_DEBUG=1 python app.py

# Terminal 2: frontend (http://localhost:3000), needs Node 22.22+ or 24
cd frontend
nvm use          # reads .nvmrc
npm ci
npm run dev
```

The Nuxt dev server proxies `/api/*` to `http://localhost:5000` (`nitro.devProxy` in `frontend/nuxt.config.ts`), so the frontend always calls `/api/...` on its own origin. If Flask is not running, searches fail after 30 s with a timeout message.

Check the production build locally: `npm run generate` writes static files to `frontend/.output/public`.

Or with Docker: `docker compose up --build` (reads `backend/.env` through `env_file` in `docker-compose.yml`)

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
| `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` | none | IGDB access for the game detail page. Register an app at [dev.twitch.tv/console](https://dev.twitch.tv/console). Without them the detail page still shows prices, only the game info is empty |

Locally, put them in `backend/.env` (git-ignored, copy from `.env.example`). Never commit them. `GET /api/health` shows `"igdb": "configured"` or `"missing"` (never the values), so you can check a deployment from the browser. `configured` only means both are set; if game info is still empty, look for `IGDB lookup failed` in the logs (e.g. a wrong secret).

## Deploy (Vercel)

`vercel.json` uses [Vercel Services](https://vercel.com/docs/services) (beta): `frontend/` is built with `nuxt generate` into static HTML (no Node server at runtime) and `backend/` runs as a Python function. `/api/*` goes to Flask, everything else to the frontend, on one domain.

Pages are prerendered at build time, so they must not fetch data on the server. `/games/<id>` cannot be prerendered (the ids are dynamic): it is client-only (`routeRules` in `nuxt.config.ts`), and `vercel.json` serves the SPA shell `200.html` for it. Any other unknown path gets `404.html`. If a page ever needs server-side data from Flask, it needs a Vercel service binding for the API URL, because relative `/api` URLs only work in the browser.

`/api/deals` and `/api/stores` answer the same for every visitor, so successful responses carry `Cache-Control: public, s-maxage=900, stale-while-revalidate=300` (`SHARED_CACHE_CONTROL` in `config.py`): the Vercel CDN keeps them 15 min. Vercel strips those directives before the browser gets the response (browsers see only `public`); locally, without Vercel, a browser may show a copy up to 5 min old while it refreshes it. Error responses are never cached. Check a deployment with the `x-vercel-cache` response header (`HIT` on a repeat request). Preview deployments are behind Vercel login, so check them in a logged-in browser, not with curl.

1. Push to GitHub
2. Import the repo on vercel.com (Root Directory: repo root)
3. Set `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` (and optionally `CHEAPSHARK_USER_AGENT`) in Project Settings → Environment Variables, for Production and Preview. Redeploy after changing them
