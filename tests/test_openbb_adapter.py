from datetime import datetime, timezone

import pytest

from lqie.data.schema import normalize_ohlcv_records
from lqie.data.providers import OpenBBCBOEAdapter


def sample_records():
    return [
        {
            "date": "2025-01-03",
            "open": 100,
            "high": 105,
            "low": 99,
            "close": 103,
            "volume": 100000,
        },
        {
            "date": "2025-01-02",
            "open": 98,
            "high": 102,
            "low": 97,
            "close": 100,
            "volume": 120000,
        },
    ]


def test_normalization_sorts_dates():
    bars = normalize_ohlcv_records(
        "spy", sample_records(), "cboe"
    )

    assert bars[0].date.isoformat() == "2025-01-02"
    assert bars[1].date.isoformat() == "2025-01-03"


def test_normalization_preserves_source_and_symbol():
    bars = normalize_ohlcv_records(
        "spy", sample_records(), "cboe"
    )

    assert bars[0].symbol == "SPY"
    assert bars[0].source == "cboe"


def test_duplicate_dates_rejected():
    records = sample_records()
    records[1]["date"] = records[0]["date"]

    with pytest.raises(ValueError, match="Duplicate"):
        normalize_ohlcv_records("SPY", records, "cboe")


def test_invalid_ohlc_rejected():
    records = sample_records()
    records[0]["high"] = 90

    with pytest.raises(ValueError, match="OHLC"):
        normalize_ohlcv_records("SPY", records, "cboe")


def test_negative_volume_rejected():
    records = sample_records()
    records[0]["volume"] = -10

    with pytest.raises(ValueError, match="volume"):
        normalize_ohlcv_records("SPY", records, "cboe")


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        normalize_ohlcv_records(
            "SPY",
            sample_records(),
            "cboe",
            datetime(2025, 1, 1),
        )


class FakeFrame:
    @property
    def empty(self):
        return False

    def reset_index(self):
        return self

    def to_dict(self, orient):
        assert orient == "records"
        return sample_records()


class FakeResult:
    provider = "cboe"
    empty = False

    def to_dataframe(self):
        return FakeFrame()


class FakeEquity:
    def historical(self, **kwargs):
        assert kwargs["symbol"] == "SPY"
        assert kwargs["start_date"] == "2025-01-02"
        return FakeResult()


class FakeOBB:
    def __init__(self):
        self.cboe = type(
            "CBOE",
            (),
            {"equity": FakeEquity()},
        )()


def test_openbb_adapter_with_mock_provider():
    adapter = OpenBBCBOEAdapter(client=FakeOBB())

    bars = adapter.fetch_ohlcv(
        "SPY",
        "2025-01-02",
        "2025-01-15",
    )

    assert len(bars) == 2
    assert bars[0].symbol == "SPY"
    assert bars[0].source == "cboe"


def test_invalid_date_range_rejected():
    adapter = OpenBBCBOEAdapter(client=FakeOBB())

    with pytest.raises(ValueError, match="start_date"):
        adapter.fetch_ohlcv(
            "SPY",
            "2025-02-01",
            "2025-01-01",
        )
