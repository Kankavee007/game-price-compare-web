from game_api.services import cheapshark
from game_api.services.stores import list_active_stores


def test_only_active_stores_sorted_by_name(monkeypatch):
    monkeypatch.setattr(cheapshark, "get_stores", lambda: [
        {"storeID": "7", "storeName": "GOG", "isActive": True, "logo": "g.png"},
        {"storeID": "4", "storeName": "Amazon", "isActive": False, "logo": None},
        {"storeID": "11", "storeName": "humble Store", "isActive": True, "logo": None},
        {"storeID": "1", "storeName": "Steam", "isActive": True, "logo": "s.png"},
    ])

    assert list_active_stores() == [
        {"storeID": "7", "storeName": "GOG", "logo": "g.png"},
        {"storeID": "11", "storeName": "humble Store", "logo": None},
        {"storeID": "1", "storeName": "Steam", "logo": "s.png"},
    ]
