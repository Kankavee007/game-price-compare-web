import re
import time

from .. import config
from ..errors import InvalidCurrencyError, InvalidParamError
from . import cheapshark, exchange

# Simple shape check (something@something.tld, no spaces). CheapShark does the real delivery;
# this only catches typos before the email leaves our server.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL_LENGTH = 254
MAX_PRICE_USD = 1000

# {(action, client ip): [timestamps of requests sent to CheapShark]}
# "set" and "manage" have separate limits, so asking for the manage email never blocks new alerts
_recent = {}


class RateLimitedError(Exception):
    """Too many alerts from one client. Routes answer 429."""


class AlertRejectedError(Exception):
    """CheapShark answered false. Routes answer 502."""


def manage_alerts(body, client_ip):
    """Validate `body` ({email}) and ask CheapShark to email a link to manage that email's alerts.

    Returns {"ok": True, "status": "sent" | "alreadySent" | "noAlerts"}.

    Raises:
        InvalidParamError: bad email
        RateLimitedError: more than ALERTS_LIMITS["manage"] requests from this IP in the window
        UpstreamError: CheapShark is down or answered something unexpected
    """
    if not isinstance(body, dict):
        raise InvalidParamError("body must be a JSON object")
    email = _email(body.get("email"))
    _check_rate_limit("manage", client_ip)
    # Each outcome gets its own message on the page. This tells the caller whether an address has
    # alerts, but CheapShark's public API already answers that for anyone (owner's choice).
    return {"ok": True, "status": cheapshark.manage_alerts(email)}


def set_alert(body, client_ip):
    """Validate `body` ({email, gameID, price, currency}) and set a CheapShark price alert.

    `price` is in `currency`; CheapShark wants USD, so it is converted with today's rate.
    Returns {"ok": True, "priceUSD": ...}.

    Raises:
        InvalidParamError / InvalidCurrencyError: bad input (message names the field)
        RateLimitedError: more than ALERTS_LIMITS["set"] alerts from this IP in the window
        AlertRejectedError: CheapShark answered false
        UpstreamError: CheapShark or er-api is down
    """
    if not isinstance(body, dict):
        raise InvalidParamError("body must be a JSON object")
    email = _email(body.get("email"))
    game_id = _game_id(body.get("gameID"))
    price = _price(body.get("price"))
    currency = body.get("currency", "USD")
    currency = currency.strip().upper() if isinstance(currency, str) else ""

    rates = exchange.get_rates()
    if currency not in rates:
        raise InvalidCurrencyError(currency)
    price_usd = round(price / rates[currency], 2)
    if price_usd < 0.01:
        raise InvalidParamError("price is too low")
    if price_usd > MAX_PRICE_USD:
        raise InvalidParamError("price is too high")

    _check_rate_limit("set", client_ip)
    if not cheapshark.set_alert(email, game_id, price_usd):
        raise AlertRejectedError(game_id)
    return {"ok": True, "priceUSD": price_usd}


def _email(value):
    email = value.strip() if isinstance(value, str) else ""
    if not email or len(email) > MAX_EMAIL_LENGTH or not EMAIL_RE.match(email):
        raise InvalidParamError("email is not a valid email address")
    return email


def _game_id(value):
    game_id = str(value).strip() if isinstance(value, (str, int)) and not isinstance(value, bool) else ""
    if not game_id:
        raise InvalidParamError("gameID is required")
    if not (game_id.isascii() and game_id.isdigit()):
        raise InvalidParamError("gameID must be a game id")
    return game_id


def _price(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise InvalidParamError("price must be a number")
    try:
        price = float(value)
    except ValueError:
        raise InvalidParamError("price must be a number") from None
    if not price > 0 or price == float("inf"):  # `not >` also rejects NaN
        raise InvalidParamError("price must be more than 0")
    return price


def _check_rate_limit(action, client_ip):
    """Count this attempt, or raise when the IP already used its ALERTS_LIMITS[action].

    Only valid requests count (it runs after validation), so typos do not use up the limit.
    """
    now = time.time()
    cutoff = now - config.ALERTS_WINDOW_SECONDS
    # Drop old entries of every IP so the dict does not grow forever
    for key in list(_recent):
        _recent[key] = [t for t in _recent[key] if t > cutoff]
        if not _recent[key]:
            del _recent[key]
    times = _recent.setdefault((action, client_ip or "unknown"), [])
    if len(times) >= config.ALERTS_LIMITS[action]:
        raise RateLimitedError()
    times.append(now)
