import time

from . import config
from .http import UpstreamError, get_json

_rates = {}
_fetched_at = 0.0


def get_rates():
    """อัตราแลกเปลี่ยนจาก USD ไปทุกสกุล cache ไว้ 30 นาที

    ถ้า API ล่มแต่ยังมี cache เก่า ใช้ของเก่าไปก่อน ดีกว่าค้นราคาไม่ได้เลย
    """
    global _rates, _fetched_at

    now = time.time()
    if _rates and now - _fetched_at < config.RATE_CACHE_SECONDS:
        return _rates

    try:
        data = get_json(config.EXCHANGE_RATE_URL)
        rates = data["rates"]
        if not isinstance(rates, dict):
            raise UpstreamError("exchange rate: unexpected response")
    except (UpstreamError, KeyError, TypeError) as err:
        if _rates:
            return _rates
        raise UpstreamError(f"exchange rate: {err}") from err

    _rates = rates
    _fetched_at = now
    return _rates
