import pytest

from game_api.services.steam import steam_cover_url


@pytest.mark.parametrize("app_id", ["400", 400, " 400 "])
def test_builds_portrait_url_from_numeric_id(app_id):
    assert steam_cover_url(app_id) == "https://shared.steamstatic.com/store_item_assets/steam/apps/400/library_600x900.jpg"


@pytest.mark.parametrize("app_id", [None, "", "0", "abc", "400/../x", "-1", "١٢٣", "4.0"])
def test_returns_none_for_missing_or_unsafe_id(app_id):
    assert steam_cover_url(app_id) is None
