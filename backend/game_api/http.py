import requests

from . import config
from .errors import UpstreamError, UpstreamNotFoundError

def _with_user_agent(headers):
    """Add our User-Agent to every request; a caller's own headers win if they set one.

    Every API gets it, not only CheapShark (which rejects generic ones like python-requests):
    it lets API owners tell our app apart, and keeps us working if another API starts blocking
    generic User-Agents. `or {}` handles callers that pass no headers (None).
    """
    return {"User-Agent": config.USER_AGENT, **(headers or {})}


def get_json(url, params=None, headers=None):
    """GET แล้วคืน JSON ใส่ timeout กับ User-Agent ให้ทุกครั้ง error ทุกแบบกลายเป็น UpstreamError"""
    data, _ = get_json_with_headers(url, params, headers)
    return data


def get_json_with_headers(url, params=None, headers=None):
    """Like get_json, but also returns the response headers.

    CheapShark /deals puts the page count in a header (X-Total-Page-Count), not in the body.
    """
    try:
        res = requests.get(
            url,
            params=params,
            headers=_with_user_agent(headers),
            timeout=config.REQUEST_TIMEOUT,
        )
        if res.status_code == 404:
            raise UpstreamNotFoundError(f"{url}: 404 Not Found")
        res.raise_for_status()
        return res.json(), res.headers
    except (requests.RequestException, ValueError) as err:
        raise UpstreamError(f"{url}: {err}") from err


def post_json(url, body, headers=None):
    """POST แล้วคืน JSON ใส่ timeout กับ User-Agent ให้ทุกครั้ง error ทุกแบบกลายเป็น UpstreamError"""
    try:
        res = requests.post(
            url,
            # FIX: was json=body. json= serializes the body as JSON, but neither API accepts that:
            # - IGDB expects a raw Apicalypse query string ("fields ...; where ...;")
            # - Twitch's token endpoint expects form fields (a dict is form-encoded, like curl --data-urlencode)
            # data= sends a str as-is and form-encodes a dict, so it covers both.
            data=body,
            headers=_with_user_agent(headers),
            timeout=config.REQUEST_TIMEOUT,
        )
        res.raise_for_status()
        return res.json()
    except (requests.RequestException, ValueError) as err:
        raise UpstreamError(f"{url}: {err}") from err