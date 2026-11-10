import os

CHEAPSHARK_BASE_URL = "https://www.cheapshark.com/api/1.0"
EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/USD"

# CheapShark ปฏิเสธ User-Agent ทั่วไปอย่าง python-requests ต้องระบุชื่อแอป
# ตั้งค่าเองได้ผ่าน env เช่น "MyApp/1.0 (contact@example.com)"
USER_AGENT = os.environ.get("CHEAPSHARK_USER_AGENT", "PriceCompareApp/1.0")

REQUEST_TIMEOUT = 10  # วินาที ต่อ request ที่ยิงไป API ภายนอก
RATE_CACHE_SECONDS = 60 * 30  # 30 นาที
STORE_CACHE_SECONDS = 60 * 60 * 24  # 1 วัน
SEARCH_LIMIT = 25  # CheapShark ให้ค้นราคาหลายเกมพร้อมกันได้สูงสุด 25 id ต่อครั้ง
