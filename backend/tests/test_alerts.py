import logging

import pytest
import requests

from game_api import create_app, http
from game_api.errors import InvalidCurrencyError, InvalidParamError, UpstreamError
from game_api.services import alerts, cheapshark, exchange

EMAIL = "player@example.com"


@pytest.fixture(autouse=True)
def fresh_limit():
    alerts._recent.clear()
    yield
    alerts._recent.clear()


@pytest.fixture
def cheapshark_calls(monkeypatch):
    calls = []

    def fake_set_alert(email, game_id, price_usd):
        calls.append((email, game_id, price_usd))
        return True

    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "set_alert", fake_set_alert)
    return calls


def body(**change):
    return {"email": EMAIL, "gameID": "82", "price": 175, "currency": "THB", **change}


# --- service -----------------------------------------------------------------------------


def test_converts_price_to_usd(cheapshark_calls):
    assert alerts.set_alert(body(), "1.1.1.1") == {"ok": True, "priceUSD": 5.0}
    assert cheapshark_calls == [(EMAIL, "82", 5.0)]


def test_usd_default_trims_email_and_accepts_int_id_and_string_price(cheapshark_calls):
    alerts.set_alert({"email": f"  {EMAIL} ", "gameID": 82, "price": "4.5"}, "1.1.1.1")
    assert cheapshark_calls == [(EMAIL, "82", 4.5)]


@pytest.mark.parametrize(
    "change, field",
    [
        ({"email": "not-an-email"}, "email"),
        ({"email": ""}, "email"),
        ({"email": "a b@c.com"}, "email"),
        ({"email": "a@" + "b" * 260 + ".com"}, "email"),
        ({"email": None}, "email"),
        ({"gameID": None}, "gameID"),
        ({"gameID": ""}, "gameID"),
        ({"gameID": "82; drop"}, "gameID"),
        ({"gameID": True}, "gameID"),
        ({"price": 0}, "price"),
        ({"price": -1}, "price"),
        ({"price": "abc"}, "price"),
        ({"price": "nan"}, "price"),
        ({"price": None}, "price"),
        ({"price": True}, "price"),
        ({"price": 0.1}, "price"),  # 0.1 THB is under 0.01 USD
        ({"price": 1_000_000}, "price"),
    ],
)
def test_invalid_fields_name_the_field(cheapshark_calls, change, field):
    with pytest.raises(InvalidParamError, match=field):
        alerts.set_alert(body(**change), "1.1.1.1")
    assert cheapshark_calls == []


def test_unknown_currency(cheapshark_calls):
    with pytest.raises(InvalidCurrencyError):
        alerts.set_alert(body(currency="XYZ"), "1.1.1.1")
    assert cheapshark_calls == []


def test_rate_limit_per_ip(cheapshark_calls):
    for _ in range(10):
        alerts.set_alert(body(), "1.1.1.1")
    with pytest.raises(alerts.RateLimitedError):
        alerts.set_alert(body(), "1.1.1.1")
    alerts.set_alert(body(), "2.2.2.2")  # another IP still works
    assert len(cheapshark_calls) == 11


def test_rate_limit_window_expires(cheapshark_calls, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(alerts.time, "time", lambda: now[0])
    for _ in range(10):
        alerts.set_alert(body(), "1.1.1.1")
    now[0] += 3601
    alerts.set_alert(body(), "1.1.1.1")
    assert len(cheapshark_calls) == 11


def test_invalid_requests_do_not_use_the_limit(cheapshark_calls):
    for _ in range(10):
        with pytest.raises(InvalidParamError):
            alerts.set_alert(body(email="bad"), "1.1.1.1")
    alerts.set_alert(body(), "1.1.1.1")


def test_cheapshark_false_is_rejected(monkeypatch):
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1})
    monkeypatch.setattr(cheapshark, "set_alert", lambda *a: False)
    with pytest.raises(alerts.AlertRejectedError):
        alerts.set_alert(body(currency="USD"), "1.1.1.1")


# --- cheapshark.set_alert ----------------------------------------------------------------


class FakeResponse:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


@pytest.mark.parametrize("payload, expected", [(True, True), (False, False), ("true", False)])
def test_cheapshark_set_alert_params(monkeypatch, payload, expected):
    seen = {}

    def fake_get(url, params=None, **kwargs):
        seen.update(url=url, params=params)
        return FakeResponse(payload)

    monkeypatch.setattr(http.requests, "get", fake_get)
    assert cheapshark.set_alert(EMAIL, "82", 4.5) is expected
    assert seen["url"].endswith("/alerts")
    assert seen["params"] == {"action": "set", "email": EMAIL, "gameID": "82", "price": "4.50"}


def test_cheapshark_error_does_not_carry_the_email(monkeypatch):
    def fail(url, params=None, **kwargs):
        raise requests.ConnectionError(f"Max retries exceeded with url: /alerts?email={EMAIL}")

    monkeypatch.setattr(http.requests, "get", fail)
    with pytest.raises(UpstreamError) as info:
        cheapshark.set_alert(EMAIL, "82", 4.5)
    assert EMAIL not in str(info.value)
    assert info.value.__cause__ is None and info.value.__suppress_context__


# --- route -------------------------------------------------------------------------------


@pytest.fixture
def client():
    return create_app().test_client()


def test_route_ok(client, cheapshark_calls):
    res = client.post("/api/alerts", json=body())
    assert res.status_code == 200
    assert res.get_json() == {"ok": True, "priceUSD": 5.0}


@pytest.mark.parametrize(
    "payload, field",
    [(body(email="x"), "email"), (body(gameID=None), "gameID"), (body(price=0), "price"),
     (body(currency="XYZ"), "currency"), (None, "body"), ([1, 2], "body")],
)
def test_route_400(client, cheapshark_calls, payload, field):
    res = client.post("/api/alerts", json=payload) if payload is not None else client.post(
        "/api/alerts", data="not json", content_type="application/json"
    )
    assert res.status_code == 400
    assert field in res.get_json()["error"]


def test_route_get_not_allowed(client):
    assert client.get("/api/alerts").status_code == 405


def test_route_429_uses_forwarded_ip(client, cheapshark_calls):
    headers = {"X-Forwarded-For": "9.9.9.9, 10.0.0.1"}
    for _ in range(10):
        assert client.post("/api/alerts", json=body(), headers=headers).status_code == 200
    res = client.post("/api/alerts", json=body(), headers=headers)
    assert res.status_code == 429
    assert res.get_json() == {"error": "Too many alerts, try later"}
    assert ("set", "9.9.9.9") in alerts._recent


@pytest.mark.parametrize(
    "fake",
    [lambda *a: False, lambda *a: (_ for _ in ()).throw(UpstreamError("CheapShark alert for game 82: request failed"))],
)
def test_route_502_and_email_not_logged(client, monkeypatch, caplog, fake):
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})
    monkeypatch.setattr(cheapshark, "set_alert", fake)
    with caplog.at_level(logging.DEBUG):
        res = client.post("/api/alerts", json=body())
    assert res.status_code == 502
    assert res.get_json() == {"error": "Could not create alert, try again later"}
    assert "82" in caplog.text
    assert EMAIL not in caplog.text


def test_email_not_logged_end_to_end(client, monkeypatch, caplog):
    """Real cheapshark.set_alert with a failing requests.get whose message holds the email."""
    monkeypatch.setattr(exchange, "get_rates", lambda: {"USD": 1, "THB": 35.0})

    def fail(url, params=None, **kwargs):
        raise requests.Timeout(f"timed out: {url}?email={params['email']}")

    monkeypatch.setattr(http.requests, "get", fail)
    with caplog.at_level(logging.DEBUG):
        res = client.post("/api/alerts", json=body())
    assert res.status_code == 502
    assert EMAIL not in caplog.text


# --- manage alerts -----------------------------------------------------------------------


@pytest.fixture
def manage_calls(monkeypatch):
    calls = []

    def fake_manage(email):
        calls.append(email)
        return "sent"

    monkeypatch.setattr(cheapshark, "manage_alerts", fake_manage)
    return calls


def test_manage_ok(client, manage_calls):
    res = client.post("/api/alerts/manage", json={"email": f" {EMAIL} "})
    assert res.status_code == 200
    assert res.get_json() == {"ok": True, "status": "sent"}
    assert manage_calls == [EMAIL]


@pytest.mark.parametrize("status", ["alreadySent", "noAlerts"])
def test_manage_passes_the_outcome(client, monkeypatch, status):
    monkeypatch.setattr(cheapshark, "manage_alerts", lambda email: status)
    res = client.post("/api/alerts/manage", json={"email": EMAIL})
    assert res.status_code == 200
    assert res.get_json() == {"ok": True, "status": status}


@pytest.mark.parametrize("payload", [{"email": "x"}, {"email": ""}, {}, [EMAIL]])
def test_manage_400(client, manage_calls, payload):
    res = client.post("/api/alerts/manage", json=payload)
    assert res.status_code == 400
    assert manage_calls == []


def test_manage_rate_limit_is_separate_from_set(client, manage_calls, cheapshark_calls):
    for _ in range(5):
        assert client.post("/api/alerts/manage", json={"email": EMAIL}).status_code == 200
    res = client.post("/api/alerts/manage", json={"email": EMAIL})
    assert res.status_code == 429
    assert res.get_json() == {"error": "Too many requests, try later"}
    assert client.post("/api/alerts", json=body()).status_code == 200  # setting still works


class TextResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


@pytest.mark.parametrize(
    "status, text, expected",
    [
        (200, "", "sent"),
        (200, "Email sent", "sent"),
        (400, "Link was already sent recently", "alreadySent"),
        (400, "No alerts found for email", "noAlerts"),
    ],
)
def test_cheapshark_manage_replies(monkeypatch, status, text, expected):
    seen = {}

    def fake_get(url, params=None, **kwargs):
        seen.update(url=url, params=params)
        return TextResponse(status, text)

    monkeypatch.setattr(http.requests, "get", fake_get)
    assert cheapshark.manage_alerts(EMAIL) == expected
    assert seen["url"].endswith("/alerts")
    assert seen["params"] == {"action": "manage", "email": EMAIL}


def test_cheapshark_manage_unexpected_reply_hides_email(monkeypatch):
    monkeypatch.setattr(
        http.requests, "get", lambda url, **kw: TextResponse(500, f"Error for {EMAIL}")
    )
    with pytest.raises(UpstreamError) as info:
        cheapshark.manage_alerts(EMAIL)
    assert "HTTP 500" in str(info.value) and "<email>" in str(info.value)
    assert EMAIL not in str(info.value)


def test_cheapshark_manage_network_error_hides_email(monkeypatch):
    def fail(url, params=None, **kwargs):
        raise requests.ConnectionError(f"url: /alerts?email={EMAIL}")

    monkeypatch.setattr(http.requests, "get", fail)
    with pytest.raises(UpstreamError) as info:
        cheapshark.manage_alerts(EMAIL)
    assert EMAIL not in str(info.value) and info.value.__suppress_context__


def test_manage_502_and_email_not_logged(client, monkeypatch, caplog):
    monkeypatch.setattr(
        http.requests, "get", lambda url, **kw: TextResponse(503, f"down, {EMAIL}")
    )
    with caplog.at_level(logging.DEBUG):
        res = client.post("/api/alerts/manage", json={"email": EMAIL})
    assert res.status_code == 502
    assert res.get_json() == {"error": "Could not send the email, try again later"}
    assert "HTTP 503" in caplog.text
    assert EMAIL not in caplog.text
