import os

CHEAPSHARK_BASE_URL = "https://www.cheapshark.com/api/1.0"
EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/USD"
IGDB_BASE_URL = "https://api.igdb.com/v4"
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")

# CheapShark ปฏิเสธ User-Agent ทั่วไปอย่าง python-requests ต้องระบุชื่อแอป
# ตั้งค่าเองได้ผ่าน env เช่น "MyApp/1.0 (contact@example.com)"
USER_AGENT = os.environ.get("CHEAPSHARK_USER_AGENT", "PriceCompareApp/1.0")

REQUEST_TIMEOUT = 10  # วินาที ต่อ request ที่ยิงไป API ภายนอก
RATE_CACHE_SECONDS = 60 * 30  # 30 นาที
STORE_CACHE_SECONDS = 60 * 60 * 24  # 1 วัน
SEARCH_LIMIT = 25  # CheapShark ให้ค้นราคาหลายเกมพร้อมกันได้สูงสุด 25 id ต่อครั้ง
DEALS_PAGE_SIZE = 30  # results per /api/deals page (CheapShark allows up to 60)
DEALS_CACHE_SECONDS = 60 * 15  # 15 นาที: landing page lists are the same for every visitor
DEALS_CACHE_MAX_ENTRIES = 200  # drop the oldest entry above this, so memory stays bounded
# Cache-Control for /api responses that are the same for every visitor (deal lists, stores).
# s-maxage: the Vercel CDN keeps them 15 min (checked on a preview 2026-11-15: MISS, then HIT).
# Vercel removes s-maxage and stale-while-revalidate before the browser gets the response, so
# browsers only see "public". Without Vercel (local Flask, Docker) a browser does see
# stale-while-revalidate and may show its copy for up to 5 min while it refreshes.
SHARED_CACHE_CONTROL = "public, s-maxage=900, stale-while-revalidate=300"
GENRES_CACHE_SECONDS = 60 * 60 * 24  # 1 วัน: IGDB genres hardly ever change
BROWSE_CACHE_SECONDS = 60 * 60 * 6  # 6 ชั่วโมง: one browse costs up to 13 upstream calls
BROWSE_LIMIT = 12  # games per genre
BROWSE_LOOKUP_WORKERS = 4  # CheapShark lookups at the same time (be polite to a free API)

# Price alerts (POST /api/alerts): best-effort limit per client IP, kept in memory per
# serverless instance, so it slows down abuse but is not a hard global limit.
# Per action: setting alerts is the normal use (one per game), the manage email is rarely needed
# and sends an email to any address typed, so it gets the lower limit.
ALERTS_LIMITS = {"set": 10, "manage": 5}  # requests per IP per window
ALERTS_WINDOW_SECONDS = 60 * 60  # 1 ชั่วโมง
