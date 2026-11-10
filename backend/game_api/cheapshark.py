import time

from . import config
from .http import UpstreamError, get_json

_store_cache = {}
_store_fetched_at = 0.0


def search_games(title):
    """ค้นเกมตามชื่อ แต่ละเกมมีราคาถูกสุด (USD) และ dealID ของร้านที่ถูกสุด"""
    data = get_json(
        f"{config.CHEAPSHARK_BASE_URL}/games",
        {"title": title, "limit": config.SEARCH_LIMIT},
    )
    if not isinstance(data, list):
        raise UpstreamError("CheapShark search: unexpected response")
    return data


def get_deal_stores(game_ids):
    """คืน {dealID: storeID} ของทุก deal ในเกมที่ระบุ (เรียก API ครั้งเดียว)"""
    if not game_ids:
        return {}
    data = get_json(f"{config.CHEAPSHARK_BASE_URL}/games", {"ids": ",".join(game_ids)})
    if not isinstance(data, dict):
        raise UpstreamError("CheapShark game lookup: unexpected response")
    return {
        deal["dealID"]: deal["storeID"]
        for game in data.values()
        if isinstance(game, dict)
        for deal in game.get("deals", [])
    }


def get_store_names():
    """คืน {storeID: storeName} cache ไว้ 1 วัน เพราะรายชื่อร้านแทบไม่เปลี่ยน"""
    global _store_cache, _store_fetched_at

    now = time.time()
    if _store_cache and now - _store_fetched_at < config.STORE_CACHE_SECONDS:
        return _store_cache

    try:
        data = get_json(f"{config.CHEAPSHARK_BASE_URL}/stores")
        _store_cache = {s["storeID"]: s["storeName"] for s in data}
        _store_fetched_at = now
    except (UpstreamError, KeyError, TypeError):
        # ชื่อร้านไม่ใช่ข้อมูลหลัก ถ้าดึงไม่ได้ใช้ cache เก่า (หรือว่าง) ไปก่อน
        pass
    return _store_cache
