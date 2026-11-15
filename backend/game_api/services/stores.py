from . import cheapshark


def list_active_stores():
    """Active stores as [{storeID, storeName, logo}], sorted by name (for the store filter).

    Raises:
        UpstreamError: CheapShark /stores failed and nothing is cached
    """
    stores = [
        {"storeID": s["storeID"], "storeName": s["storeName"], "logo": s["logo"]}
        for s in cheapshark.get_stores()
        if s["isActive"]
    ]
    return sorted(stores, key=lambda s: s["storeName"].casefold())
