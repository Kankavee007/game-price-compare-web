import pytest

from game_api import http


@pytest.fixture(autouse=True)
def no_real_http(monkeypatch):
    """Fail any test that would call a real external API.

    Tests must fake the service function they depend on (cheapshark.get_games, ...). Without
    this guard a missing fake silently hits CheapShark: slow, flaky, and the test passes or
    fails depending on live prices.
    """

    def blocked(url, *args, **kwargs):
        pytest.fail(f"test made a real HTTP request to {url}; fake the service call instead")

    monkeypatch.setattr(http.requests, "get", blocked)
    monkeypatch.setattr(http.requests, "post", blocked)
