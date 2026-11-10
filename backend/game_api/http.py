import requests

from . import config
from .errors import UpstreamError


def get_json(url, params=None):
    """GET แล้วคืน JSON ใส่ timeout กับ User-Agent ให้ทุกครั้ง error ทุกแบบกลายเป็น UpstreamError"""
    try:
        res = requests.get(
            url,
            params=params,
            headers={"User-Agent": config.USER_AGENT},
            timeout=config.REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        return res.json()
    except (requests.RequestException, ValueError) as err:
        raise UpstreamError(f"{url}: {err}") from err
