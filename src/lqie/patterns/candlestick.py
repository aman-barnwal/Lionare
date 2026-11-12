"""TA-Lib candlestick recognition adapter."""

import numpy as np
import talib

from lqie.patterns.types import PatternDetection


def detect_candlesticks(
    frame,
    symbol: str,
    timeframe: str,
) -> list[PatternDetection]:

    opened = frame["Open"].to_numpy(dtype=np.float64)
    high = frame["High"].to_numpy(dtype=np.float64)
    low = frame["Low"].to_numpy(dtype=np.float64)
    close = frame["Close"].to_numpy(dtype=np.float64)

    latest_index = len(frame) - 1
    latest_time = frame["Datetime"].iloc[-1].isoformat()

    results = []
    functions = talib.get_function_groups()["Pattern Recognition"]

    for function_name in functions:
        function = getattr(talib, function_name)

        try:
            values = function(opened, high, low, close)
            raw_value = float(values[-1])
        except Exception:
            continue

        if not np.isfinite(raw_value) or raw_value == 0:
            continue

        direction = "bullish" if raw_value > 0 else "bearish"
        pattern_name = function_name.removeprefix("CDL").lower()

        results.append(
            PatternDetection(
                symbol=symbol.upper(),
                timeframe=timeframe,
                engine="talib",
                category="candlestick",
                pattern=pattern_name,
                direction=direction,
                start_time=latest_time,
                end_time=latest_time,
                end_index=latest_index,
                algorithm_score=abs(raw_value),
                metadata={
                    "talib_function": function_name,
                    "raw_output": int(raw_value),
                    "score_interpretation": (
                        "Native TA-Lib pattern output. "
                        "Not a calibrated probability."
                    ),
                },
            )
        )

    return results
