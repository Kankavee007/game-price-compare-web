import pytest

from game_api.services.lowest import lowest_price_fields


def test_converts_and_formats_date():
    assert lowest_price_fields({"price": "2.00", "date": 1534118400}, 3.0, 35.0) == {
        "lowestPriceEver": 70.0,
        "lowestPriceEverDate": "2018-08-13",
        "isHistoricalLow": False,
    }


@pytest.mark.parametrize("current, expected", [(2.0, True), (1.5, True), (2.01, False), (None, False)])
def test_historical_low_compares_usd(current, expected):
    assert lowest_price_fields({"price": "2.00", "date": 1}, current, 35.0)["isHistoricalLow"] is expected


def test_rounding_in_another_currency_cannot_flip_it():
    # 0.333 and 0.334 both show as 0.33 EUR at rate 1.0, but only the real USD prices count
    assert lowest_price_fields({"price": "0.333"}, 0.334, 1.0)["isHistoricalLow"] is False


@pytest.mark.parametrize("data", [None, {}, {"price": None}, {"price": "abc"}])
def test_missing_or_bad_data_gives_nulls(data):
    assert lowest_price_fields(data, 1.0, 1.0) == {
        "lowestPriceEver": None,
        "lowestPriceEverDate": None,
        "isHistoricalLow": False,
    }


def test_missing_date_only_nulls_the_date():
    fields = lowest_price_fields({"price": "1.00"}, 1.0, 1.0)
    assert fields["lowestPriceEverDate"] is None
    assert fields["isHistoricalLow"] is True
