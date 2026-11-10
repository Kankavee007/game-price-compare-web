import requests

from . import config


class UpstreamError(Exception):
    """API ภายนอก (CheapShark / er-api) ล่ม ช้าเกิน หรือตอบผิดรูปแบบ"""


def get_json(url, params=None):
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
