"""PyTrendline support and resistance adapter."""

import math

import pandas as pd
import pytrendline

from lqie.patterns.types import PatternDetection


def detect_trendlines(
    frame,
    symbol: str,
    timeframe: str,
    max_bars: int = 180,
    max_lines_per_side: int = 10,
) -> list[PatternDetection]:

    if len(frame) < 30:
        return []

    offset = max(0, len(frame) - max_bars)
    window = frame.iloc[offset:].reset_index(drop=True)

    candles = pd.DataFrame({
        "Date": window["Datetime"],
        "Open": window["Open"].astype(float),
        "High": window["High"].astype(float),
        "Low": window["Low"].astype(float),
        "Close": window["Close"].astype(float),
    })

    candles["Volume"] = window["Volume"].astype(float)

    supported_intervals = {
        "1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d"
    }

    interval = (
        timeframe if timeframe in supported_intervals else "1d"
    )

    candle_data = pytrendline.CandlestickData(
        df=candles,
        time_interval=interval,
        open_col="Open",
        high_col="High",
        low_col="Low",
        close_col="Close",
        datetime_col="Date",
    )

    result = pytrendline.detect(
        candlestick_data=candle_data,
        trend_type=pytrendline.TrendlineTypes.BOTH,
        first_pt_must_be_pivot=True,
        last_pt_must_be_pivot=True,
        all_pts_must_be_pivots=False,
        min_points_required=3,
        ignore_breakouts=True,
        debug=False,
    )

    detections = []

    for side in ("support", "resistance"):
        key = f"{side}_trendlines"
        table = result.get(key)

        if table is None or table.empty:
            continue

        for _, row in table.sort_values(
            "score", ascending=False
        ).head(max_lines_per_side).iterrows():

            def finite_float(value):
                try:
                    value = float(value)
                    return value if math.isfinite(value) else None
                except (TypeError, ValueError):
                    return None

            local_start = int(row["starts_at_index"])
            local_end = int(row["ends_at_index"])

            start_date = row.get("starts_at_date")
            end_date = row.get("ends_at_date")

            metadata = {
                "num_points": int(row["num_points"]),
                "slope": finite_float(row["slope"]),
                "intercept": finite_float(row["b"]),
                "breakout": bool(row["is_breakout"]),
                "point_indices": list(row["pointset_indeces"]),
                "trendline_rank": (
                    int(row["overall_rank"])
                    if pd.notna(row["overall_rank"]) else None
                ),
                "score_note": (
                    "Native PyTrendline algorithm score; "
                    "not a probability."
                ),
                "scan_window_bars": len(window),
            }

            detections.append(
                PatternDetection(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    engine="pytrendline",
                    category="trendline",
                    pattern=f"{side}_trendline",
                    direction="neutral",
                    start_time=(
                        start_date.isoformat()
                        if hasattr(start_date, "isoformat")
                        else str(start_date)
                    ),
                    end_time=(
                        end_date.isoformat()
                        if hasattr(end_date, "isoformat")
                        else str(end_date)
                    ),
                    start_index=offset + local_start,
                    end_index=offset + local_end,
                    reference_price=finite_float(
                        row["price_at_last_date"]
                    ),
                    algorithm_score=finite_float(row["score"]),
                    metadata=metadata,
                )
            )

    return detections
