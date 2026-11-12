import numpy as np
import pandas as pd
import pytest

from lqie.patterns import PatternEngine, normalize_ohlcv
from lqie.patterns.candlestick import detect_candlesticks
from lqie.features.pattern_features import build_pattern_feature_row


def make_candles(n=220):
    rng = np.random.default_rng(42)
    x = np.arange(n, dtype=float)

    close = (
        100
        + 0.07 * x
        + 4 * np.sin(x / 6)
        + 2 * np.sin(x / 17)
        + rng.normal(0, 0.15, n)
    )

    opened = close + rng.normal(0, 0.25, n)
    high = np.maximum(opened, close) + rng.uniform(0.1, 0.8, n)
    low = np.minimum(opened, close) - rng.uniform(0.1, 0.8, n)

    return pd.DataFrame({
        "Date": pd.date_range(
            "2023-01-01",
            periods=n,
            freq="D",
            tz="UTC",
        ),
        "Open": opened,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": rng.integers(10000, 100000, n),
    })


def test_normalize_ohlcv():
    frame = normalize_ohlcv(make_candles())

    assert len(frame) == 220

    assert list(frame.columns) == [
        "Datetime",
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    assert frame["Datetime"].is_monotonic_increasing


def test_invalid_ohlc_rejected():
    data = pd.DataFrame({
        "Date": [
            "2026-01-01",
            "2026-01-02",
            "2026-01-03",
        ],
        "Open": [10, 10, 10],
        "High": [9, 11, 11],
        "Low": [8, 8, 8],
        "Close": [9, 10, 10],
        "Volume": [100, 100, 100],
    })

    with pytest.raises(ValueError, match="High"):
        normalize_ohlcv(data)


def test_duplicate_timestamps_rejected():
    frame = make_candles(10)
    frame.loc[1, "Date"] = frame.loc[0, "Date"]

    with pytest.raises(ValueError, match="Duplicate"):
        normalize_ohlcv(frame)


def test_talib_bullish_engulfing_detection():
    frame = make_candles(40)

    frame.loc[38, ["Open", "High", "Low", "Close"]] = [
        10.5, 10.6, 9.4, 9.5
    ]

    frame.loc[39, ["Open", "High", "Low", "Close"]] = [
        9.4, 10.9, 9.3, 10.8
    ]

    normalized = normalize_ohlcv(frame)

    detections = detect_candlesticks(
        normalized,
        "TEST",
        "1d",
    )

    assert any(
        item.pattern == "engulfing"
        and item.direction == "bullish"
        for item in detections
    )


def test_engine_calculates_indicators():
    result = PatternEngine().analyze(
        make_candles(),
        "TEST",
        include_trendlines=False,
        include_harmonics=False,
        include_regimes=False,
    )

    assert result["symbol"] == "TEST"
    assert result["bars_analysed"] == 220
    assert result["indicators"]["rsi_14"] is not None
    assert result["indicators"]["atr_14"] is not None


def test_engine_returns_standardised_detections():
    result = PatternEngine().analyze(
        make_candles(),
        "TEST",
        include_trendlines=False,
        include_harmonics=False,
        include_regimes=False,
    )

    for item in result["detections"]:
        assert item["symbol"] == "TEST"
        assert item["engine"] == "talib"
        assert item["category"] == "candlestick"
        assert item["direction"] in ("bullish", "bearish")


def test_pattern_feature_generation():
    result = PatternEngine().analyze(
        make_candles(),
        "TEST",
        include_trendlines=False,
        include_harmonics=False,
        include_regimes=False,
    )

    features = build_pattern_feature_row(result)

    assert features["symbol"] == "TEST"
    assert "candlestick_count" in features
    assert "indicator_rsi_14" in features
