"""Technical indicator calculations for LQIE."""

import numpy as np
import talib


def _last_valid(values):
    if values is None or len(values) == 0:
        return None

    value = float(values[-1])
    return value if np.isfinite(value) else None


def calculate_indicators(frame) -> dict:
    close = frame["Close"].to_numpy(dtype=np.float64)
    high = frame["High"].to_numpy(dtype=np.float64)
    low = frame["Low"].to_numpy(dtype=np.float64)

    result = {}

    if len(close) >= 15:
        result["rsi_14"] = _last_valid(
            talib.RSI(close, timeperiod=14)
        )
        result["atr_14"] = _last_valid(
            talib.ATR(high, low, close, timeperiod=14)
        )
        result["adx_14"] = _last_valid(
            talib.ADX(high, low, close, timeperiod=14)
        )

    if len(close) >= 34:
        macd, signal, histogram = talib.MACD(close)

        result["macd"] = {
            "value": _last_valid(macd),
            "signal": _last_valid(signal),
            "histogram": _last_valid(histogram),
        }

    for period in (20, 50, 100, 200):
        if len(close) >= period:
            result[f"sma_{period}"] = _last_valid(
                talib.SMA(close, timeperiod=period)
            )
            result[f"ema_{period}"] = _last_valid(
                talib.EMA(close, timeperiod=period)
            )

    if len(close) >= 20:
        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2,
        )
        result["bollinger"] = {
            "upper": _last_valid(upper),
            "middle": _last_valid(middle),
            "lower": _last_valid(lower),
        }

    return result
