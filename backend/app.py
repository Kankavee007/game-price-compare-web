from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time

app = Flask(__name__)
CORS(app)

rate_cache = {}
last_fetch_time = 0
CACHE_DURATION = 60 * 30  # 30 นาที

@app.route("/api/search")
def search():
    query = request.args.get("query")
    currency = request.args.get("currency", "USD")

    url = f"https://www.cheapshark.com/api/1.0/games?title={query}"
    res = requests.get(url)
    data = res.json()

    rate = get_exchange_rate(currency)

    result = []
    for game in data[:10]:
        usd_price = float(game["cheapest"])
        converted = usd_price * rate

        result.append({
            "name": game["external"],
            "price": round(converted, 2),
            "currency": currency,
            "thumb": game["thumb"],
            "storeID": game["cheapestDealID"][:1]  # workaround ง่าย (หรือ map จริงทีหลัง)
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
    app.run(debug=True)