"""HarmonicPatterns adapter for LQIE."""

from harmonic_patterns import HarmonicDetector

from lqie.patterns.types import PatternDetection


def detect_harmonics(
    frame,
    symbol: str,
    timeframe: str,
    error_allowed: float = 0.05,
) -> list[PatternDetection]:

    if len(frame) < 60:
        return []

    import pandas as pd

    data = pd.DataFrame({
        "open": frame["Open"].astype(float).to_numpy(),
        "high": frame["High"].astype(float).to_numpy(),
        "low": frame["Low"].astype(float).to_numpy(),
        "close": frame["Close"].astype(float).to_numpy(),
        "volume": frame["Volume"].astype(float).to_numpy(),
    }, index=pd.DatetimeIndex(frame["Datetime"]))

    detector = HarmonicDetector(
        error_allowed=error_allowed,
        strict=True,
    )

    completed, predicted = detector.search_patterns(
        data,
        predict=True,
        only_last=True,
        last_n=1,
        plot=False,
        plot_predict=False,
        return_dt_idx=True,
    )

    detections = []

    for is_prediction, collection in (
        (False, completed),
        (True, predicted),
    ):
        for item in collection:
            points, point_dates, label, ratios = item

            label = str(label)
            lower_label = label.lower()

            if lower_label.startswith("bullish"):
                direction = "bullish"
            elif lower_label.startswith("bearish"):
                direction = "bearish"
            else:
                direction = "neutral"

            start_time = (
                point_dates[0].isoformat()
                if hasattr(point_dates[0], "isoformat")
                else str(point_dates[0])
            )

            end_time = (
                point_dates[-1].isoformat()
                if hasattr(point_dates[-1], "isoformat")
                else str(point_dates[-1])
            )

            point_indices = [int(point[2]) for point in points]

            target = ratios.get("predict_D")

            try:
                target = float(target) if target is not None else None
            except (TypeError, ValueError):
                target = None

            detections.append(
                PatternDetection(
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    engine="harmonic_patterns",
                    category="harmonic",
                    pattern=label,
                    direction=direction,
                    start_time=start_time,
                    end_time=end_time,
                    start_index=(
                        point_indices[0] if point_indices else None
                    ),
                    end_index=(
                        len(frame) - 1
                        if is_prediction
                        else point_indices[-1]
                    ),
                    reference_price=target,
                    is_prediction=is_prediction,
                    metadata={
                        "ratios": ratios,
                        "pivot_points": points,
                        "pivot_indices": point_indices,
                        "target_D": target,
                        "warning": (
                            "Harmonic completion projection is a candidate "
                            "price level, not a forecast probability."
                        ),
                    },
                )
            )

    return detections
