import os
import time

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

rate_cache = {}
last_fetch_time = 0
CACHE_DURATION = 60 * 30  # 30 นาที

# CheapShark ปฏิเสธ User-Agent ทั่วไปอย่าง python-requests ต้องระบุชื่อแอป
# ตั้งค่าเองได้ผ่าน env เช่น "MyApp/1.0 (contact@example.com)"
HEADERS = {"User-Agent": os.environ.get("CHEAPSHARK_USER_AGENT", "PriceCompareApp/1.0")}

@app.route("/api/search")
def search():
    query = request.args.get("query")
    currency = request.args.get("currency", "USD")

    url = "https://www.cheapshark.com/api/1.0/games"
    res = requests.get(url, params={"title": query}, headers=HEADERS)
    data = res.json()

    rate = get_exchange_rate(currency)

    result = []
    for game in data:
        usd_price = float(game["cheapest"])
        converted = usd_price * rate

        result.append({
            "name": game["external"],
            "price": round(converted, 2),
            "currency": currency,
            "thumb": game["thumb"],
            "storeID": game["cheapestDealID"][:1],  # workaround ง่าย (หรือ map จริงทีหลัง)
            "dealUrl": f"https://www.cheapshark.com/redirect?dealID={game['cheapestDealID']}"
        })

    return jsonify(result)

def get_exchange_rate(to_currency):
    global rate_cache, last_fetch_time

    now = time.time()

    # ถ้า cache ยังใช้ได้
    if rate_cache and (now - last_fetch_time < CACHE_DURATION):
        return rate_cache.get(to_currency, 1)

    # ถ้า cache หมดอายุ → เรียก API ใหม่
    url = "https://open.er-api.com/v6/latest/USD"
    res = requests.get(url)
    data = res.json()

    rate_cache = data["rates"]
    last_fetch_time = now

    return rate_cache.get(to_currency, 1)

@app.route("/api/test")
def test():
    return jsonify({"msg": "backend working"})

if __name__ == "__main__":
    # Local development only. Production (Vercel) imports `app` directly.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )