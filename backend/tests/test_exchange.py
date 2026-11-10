import pytest

from game_api.errors import UpstreamError
from game_api.services import exchange


def down(url, params=None):
    raise UpstreamError("down")


def test_uses_stale_cache_when_api_down(monkeypatch):
    monkeypatch.setattr(exchange, "_rates", {"THB": 30.0})
    monkeypatch.setattr(exchange, "_fetched_at", 0.0)  # expired
    monkeypatch.setattr(exchange, "get_json", down)

    assert exchange.get_rates() == {"THB": 30.0}


def test_raises_without_cache(monkeypatch):
    monkeypatch.setattr(exchange, "_rates", {})
    monkeypatch.setattr(exchange, "get_json", down)

    with pytest.raises(UpstreamError):
        exchange.get_rates()
