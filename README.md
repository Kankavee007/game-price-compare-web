# game-price-compare-web

My first web project by myself

ค้นหาราคาเกมที่ถูกที่สุดจาก [CheapShark](https://www.cheapshark.com/) และแปลงสกุลเงินด้วย [open.er-api.com](https://open.er-api.com/)

- `frontend/`: Vue 3 + Vite + Tailwind CSS
- `backend/`: Flask (`/api/search`)

## Run locally

```bash
# Terminal 1: backend (http://localhost:5000)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
FLASK_DEBUG=1 python app.py

# Terminal 2: frontend (http://localhost:5173)
cd frontend
npm ci
npm run dev
```

Vite proxies `/api/*` to `http://localhost:5000` (`frontend/vite.config.ts`), so the frontend always calls `/api/...` on its own origin.

Or with Docker: `docker compose up --build`

### Environment variables (backend)

| Name | Default | Purpose |
|---|---|---|
| `CHEAPSHARK_USER_AGENT` | `PriceCompareApp/1.0` | CheapShark rejects generic User-Agents. Set e.g. `MyApp/1.0 (you@example.com)` |
| `FLASK_DEBUG` | off | `1` enables debug mode. Never on in production |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Local server bind address |

## Deploy (Vercel)

`vercel.json` uses [Vercel Services](https://vercel.com/docs/services) (beta): `frontend/` is built as a Vite static site and `backend/` runs as a Python function. `/api/*` goes to Flask, everything else to the frontend, on one domain.

1. Push to GitHub
2. Import the repo on vercel.com (Root Directory: repo root)
3. (Optional) set `CHEAPSHARK_USER_AGENT` in Project Settings → Environment Variables
