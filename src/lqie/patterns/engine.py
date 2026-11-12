"""Unified LQIE pattern and technical-analysis engine."""

from datetime import datetime, timezone

from lqie.patterns.base import normalize_ohlcv
from lqie.patterns.candlestick import detect_candlesticks
from lqie.patterns.harmonic import detect_harmonics
from lqie.patterns.indicators import calculate_indicators
from lqie.patterns.regimes import detect_regime_changes
from lqie.patterns.trendlines import detect_trendlines


class PatternEngine:
    VERSION = "0.5.0"

    def analyze(
        self,
        data,
        symbol: str,
        timeframe: str = "1d",
        include_trendlines: bool = True,
        include_harmonics: bool = True,
        include_regimes: bool = True,
    ) -> dict:

        symbol = symbol.strip().upper()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        frame = normalize_ohlcv(data)

        detections = []
        errors = {}

        indicators = calculate_indicators(frame)
        latest = frame.iloc[-1]

        def execute(name, function):
            try:
                found = function()
                detections.extend(found)
                print(f"{name}: {len(found)} detections")
            except Exception as exc:
                errors[name] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
                print(f"{name} ERROR: {type(exc).__name__}: {exc}")

        execute(
            "candlesticks",
            lambda: detect_candlesticks(frame, symbol, timeframe),
        )

        if include_trendlines:
            execute(
                "trendlines",
                lambda: detect_trendlines(frame, symbol, timeframe),
            )

        if include_harmonics:
            execute(
                "harmonics",
                lambda: detect_harmonics(frame, symbol, timeframe),
            )

        if include_regimes:
            execute(
                "regimes",
                lambda: detect_regime_changes(frame, symbol, timeframe),
            )

        return {
            "schema_version": 1,
            "engine_version": self.VERSION,
            "symbol": symbol,
            "timeframe": timeframe,
            "analysed_at_utc": datetime.now(timezone.utc).isoformat(),
            "bars_analysed": len(frame),
            "first_bar": frame["Datetime"].iloc[0].isoformat(),
            "last_bar": frame["Datetime"].iloc[-1].isoformat(),
            "latest_bar": {
                "datetime": latest["Datetime"].isoformat(),
                "open": float(latest["Open"]),
                "high": float(latest["High"]),
                "low": float(latest["Low"]),
                "close": float(latest["Close"]),
                "volume": float(latest["Volume"]),
            },
            "indicators": indicators,
            "detections": [item.to_dict() for item in detections],
            "detection_count": len(detections),
            "errors": errors,
            "model_status": "pattern_engine_not_a_trained_predictor",
        }
