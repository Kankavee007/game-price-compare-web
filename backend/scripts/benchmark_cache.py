"""Count how many upstream API calls the backend makes, with the in-memory caches on vs off.

Run from backend/ (needs the backend requirements installed):

    python scripts/benchmark_cache.py                    # 20 visits, every scenario
    python scripts/benchmark_cache.py --visits 50
    python scripts/benchmark_cache.py --scenario landing --verbose

No real API is called. Nothing leaves the machine, so it is safe to run as often as you like
(CheapShark rate limits do not apply).

How a call is counted
---------------------
Every outbound request in the backend goes through game_api/http.py, which calls
`requests.get` or `requests.post`. This script replaces those two functions with fakes
(see FakeUpstream). Each time the backend calls one of them, the fake:

  1. adds 1 to a counter for that endpoint (e.g. "CheapShark GET /deals"),
  2. returns made-up JSON shaped like the real API's answer.

A cache hit returns before http.py is reached, so it is NOT counted. A cache miss goes
through http.py, so it IS counted. "API calls" therefore means "requests that would have
gone to CheapShark / er-api / Twitch / IGDB in production".

A URL the fake does not know raises an error instead of reaching the internet.

Cache on vs off
---------------
Both runs send exactly the same /api requests through the real Flask app (test client):

- on:  the real cache lifetimes from config.py.
- off: every *_CACHE_SECONDS set to -1, so a saved answer is always too old, and the
       fake Twitch token expires at once. Every request then goes upstream.

Each run starts with empty caches, like a freshly started server.

Limits
------
- One process = one cache. On Vercel each serverless instance has its own cache, so real
  savings are lower than this.
- The Vercel CDN cache (Cache-Control: s-maxage) is not measured here; it needs a deploy.
- Every visit happens within a few seconds, so no cache entry expires during a run.
"""

import argparse
import collections
import os
import sys
from urllib.parse import urlparse

# Make `game_api` importable when run as `python scripts/benchmark_cache.py` from backend/
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# IGDB code refuses to run without these; the fake never sends them anywhere
os.environ.setdefault("TWITCH_CLIENT_ID", "benchmark-fake-id")
os.environ.setdefault("TWITCH_CLIENT_SECRET", "benchmark-fake-secret")

from game_api import config, create_app, http  # noqa: E402
from game_api.services import browse, cheapshark, exchange, igdb  # noqa: E402

# The /api requests one page visit makes, copied from the frontend:
#   landing: SearchFilters.vue (/api/stores), the 3 GameSection lists in pages/index.vue,
#            DiscountSidebar.vue
#   browse:  pages/browse.vue (/api/genres, then the default genre)
SCENARIOS = {
    "landing": [
        "/api/stores",
        "/api/deals?currency=USD&sort=rating&onSale=1",               # Top rated
        "/api/deals?currency=USD&sort=newest&minRating=80&onSale=1",  # New releases
        "/api/deals?currency=USD&maxPrice=0&onSale=1",                # Free now
        "/api/deals?currency=USD&sort=savings&onSale=1&minRating=80", # Discount sidebar
    ],
    "browse": [
        "/api/genres",
        "/api/browse?genre=12&currency=USD",
    ],
}

CACHE_SETTINGS = [
    "RATE_CACHE_SECONDS",
    "STORE_CACHE_SECONDS",
    "DEALS_CACHE_SECONDS",
    "GAMES_CACHE_SECONDS",
    "GENRES_CACHE_SECONDS",
    "BROWSE_CACHE_SECONDS",
]


class FakeResponse:
    """The parts of requests.Response that game_api/http.py uses."""

    def __init__(self, data, headers=None):
        self.status_code = 200
        self.headers = headers or {}
        self._data = data
        self.text = ""

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


class FakeUpstream:
    """Stands in for requests.get / requests.post and counts every call."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.token_lifetime = 3600  # seconds; 0 when caches are off
        self.counts = collections.Counter()

    def _count(self, label):
        self.counts[label] += 1
        if self.verbose:
            print(f"      upstream call: {label}")

    def get(self, url, params=None, **_kwargs):
        params = params or {}
        path = urlparse(url).path

        if url == config.EXCHANGE_RATE_URL:
            self._count("er-api GET /latest/USD")
            return FakeResponse({"rates": {"USD": 1, "EUR": 0.92, "THB": 35.5}})

        if url.startswith(config.CHEAPSHARK_BASE_URL):
            if path.endswith("/stores"):
                self._count("CheapShark GET /stores")
                return FakeResponse([
                    {"storeID": "1", "storeName": "Steam", "isActive": 1, "images": {"logo": "/img/1.png"}},
                    {"storeID": "7", "storeName": "GOG", "isActive": 1, "images": {"logo": "/img/7.png"}},
                ])
            if path.endswith("/deals"):
                self._count("CheapShark GET /deals")
                free = str(params.get("upperPrice")) in ("0", "0.0")
                rows = [_deal_row(i, free) for i in range(int(params.get("pageSize", 30)))]
                return FakeResponse(rows, {"X-Total-Page-Count": "5"})
            if path.endswith("/games") and "ids" in params:
                self._count("CheapShark GET /games?ids= (lowest price ever)")
                return FakeResponse({
                    gid: {"info": {"title": f"Game {gid}"},
                          "cheapestPriceEver": {"price": "0.99", "date": 1600000000},
                          "deals": []}
                    for gid in params["ids"].split(",")
                })
            if path.endswith("/games") and "steamAppID" in params:
                self._count("CheapShark GET /games?steamAppID= (browse price)")
                return FakeResponse([{"gameID": params["steamAppID"], "cheapest": "4.99",
                                      "steamAppID": params["steamAppID"], "thumb": ""}])

        raise RuntimeError(f"benchmark: no fake for GET {url}; refusing to call the real API")

    def post(self, url, data=None, **_kwargs):
        if url.startswith("https://id.twitch.tv/oauth2/token"):
            self._count("Twitch POST /oauth2/token")
            return FakeResponse({"access_token": "fake-token", "expires_in": self.token_lifetime})

        if url.startswith(config.IGDB_BASE_URL):
            path = urlparse(url).path
            if path.endswith("/genres"):
                self._count("IGDB POST /genres")
                return FakeResponse([{"id": 12, "name": "Role-playing (RPG)"}, {"id": 5, "name": "Shooter"}])
            if path.endswith("/games"):
                self._count("IGDB POST /games")
                return FakeResponse([
                    {"id": i, "name": f"IGDB game {i}", "total_rating": 85,
                     "cover": {"image_id": f"co{i}"},
                     "external_games": [{"uid": str(1000 + i), "external_game_source": 1}]}
                    for i in range(config.BROWSE_LIMIT)
                ])

        raise RuntimeError(f"benchmark: no fake for POST {url}; refusing to call the real API")


def _deal_row(i, free):
    price = "0.00" if free else f"{4.99 + i:.2f}"
    return {
        "gameID": str(100 + i), "dealID": f"deal{i}", "storeID": "1", "title": f"Deal game {i}",
        "salePrice": price, "normalPrice": "29.99", "savings": "80", "isOnSale": "1",
        "metacriticScore": "85", "steamRatingPercent": "90", "steamAppID": str(1000 + i),
        "releaseDate": 1600000000, "dealRating": "9.0", "thumb": "",
    }


def reset_caches():
    """Empty every in-memory cache, like a freshly started server."""
    cheapshark._deals_cache.clear()
    cheapshark._games_cache.clear()
    cheapshark._stores = []
    cheapshark._store_fetched_at = 0.0
    exchange._rates = {}
    exchange._fetched_at = 0.0
    igdb._token = None
    igdb._token_expired_at = 0.0
    browse._genres = []
    browse._genres_fetched_at = 0.0
    browse._browse_cache.clear()


def run(paths, visits, cache_on, fake, original_settings):
    """Send `visits` page visits through the Flask app; returns (counts, per-visit totals, statuses)."""
    for name, value in original_settings.items():
        setattr(config, name, value if cache_on else -1)
    fake.token_lifetime = 3600 if cache_on else 0
    reset_caches()
    fake.counts.clear()

    client = create_app().test_client()
    per_visit = []
    statuses = collections.Counter()
    for visit in range(1, visits + 1):
        before = sum(fake.counts.values())
        if fake.verbose:
            print(f"    visit {visit}")
        for path in paths:
            if fake.verbose:
                print(f"    GET {path}")
            statuses[client.get(path).status_code] += 1
        per_visit.append(sum(fake.counts.values()) - before)
    return dict(fake.counts), per_visit, statuses


def describe_visits(per_visit):
    """e.g. 'visit 1: 9, visits 2-20: 3 each'"""
    if len(per_visit) == 1 or len(set(per_visit[1:])) > 1:
        return ", ".join(str(n) for n in per_visit)
    if per_visit[0] == per_visit[1]:
        return f"{per_visit[0]} each"
    return f"visit 1: {per_visit[0]}, visits 2-{len(per_visit)}: {per_visit[1]} each"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--visits", type=int, default=20, help="page visits per run (default 20)")
    parser.add_argument("--scenario", choices=[*SCENARIOS, "all"], default="all")
    parser.add_argument("--verbose", action="store_true", help="print every /api request and upstream call")
    args = parser.parse_args()
    if args.visits < 1:
        parser.error("--visits must be at least 1")

    fake = FakeUpstream(verbose=args.verbose)
    http.requests.get = fake.get
    http.requests.post = fake.post
    original_settings = {name: getattr(config, name) for name in CACHE_SETTINGS}

    names = SCENARIOS if args.scenario == "all" else [args.scenario]
    for name in names:
        paths = SCENARIOS[name]
        print(f"\n=== {name}: {args.visits} visits x {len(paths)} /api requests ===")
        results = {}
        for cache_on in (False, True):
            label = "on" if cache_on else "off"
            if args.verbose:
                print(f"\n  --- cache {label} ---")
            results[label] = run(paths, args.visits, cache_on, fake, original_settings)

        endpoints = sorted(set(results["off"][0]) | set(results["on"][0]))
        width = max(len(e) for e in endpoints)
        print(f"\n  {'upstream endpoint':<{width}}  {'cache off':>9}  {'cache on':>8}")
        for endpoint in endpoints:
            print(f"  {endpoint:<{width}}  {results['off'][0].get(endpoint, 0):>9}  "
                  f"{results['on'][0].get(endpoint, 0):>8}")
        total_off, total_on = sum(results["off"][1]), sum(results["on"][1])
        print(f"  {'TOTAL':<{width}}  {total_off:>9}  {total_on:>8}")

        saved = total_off - total_on
        percent = saved / total_off * 100 if total_off else 0
        print(f"\n  saved {saved} calls ({percent:.0f}%)")
        print(f"  calls per visit, cache off: {describe_visits(results['off'][1])}")
        print(f"  calls per visit, cache on:  {describe_visits(results['on'][1])}")
        for label in ("off", "on"):
            statuses = results[label][2]
            if set(statuses) != {200}:
                print(f"  WARNING: cache {label} got non-200 answers: {dict(statuses)}")


if __name__ == "__main__":
    main()
