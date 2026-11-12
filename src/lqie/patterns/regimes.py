"""Offline market regime change detection using Ruptures."""

import numpy as np
import ruptures as rpt

from lqie.patterns.types import PatternDetection


def detect_regime_changes(
    frame,
    symbol: str,
    timeframe: str,
    penalty: float = 5.0,
    min_segment_size: int = 20,
) -> list[PatternDetection]:

    close = frame["Close"].to_numpy(dtype=np.float64)

    if len(close) < min_segment_size * 3:
        return []

    log_returns = np.diff(np.log(close))
    volatility_component = np.abs(log_returns)

    signal = np.column_stack([
        log_returns,
        volatility_component,
    ])

    algorithm = rpt.Pelt(
        model="rbf",
        min_size=min_segment_size,
        jump=5,
    ).fit(signal)

    breakpoints = algorithm.predict(pen=float(penalty))

    detections = []

    for boundary in breakpoints[:-1]:
        index = min(int(boundary), len(frame) - 1)
        timestamp = frame["Datetime"].iloc[index].isoformat()

        detections.append(
            PatternDetection(
                symbol=symbol.upper(),
                timeframe=timeframe,
                engine="ruptures",
                category="regime",
                pattern="statistical_change_point",
                direction="neutral",
                start_time=timestamp,
                end_time=timestamp,
                start_index=index,
                end_index=index,
                metadata={
                    "method": "PELT",
                    "model": "rbf",
                    "penalty": float(penalty),
                    "minimum_segment_size": min_segment_size,
                    "components": [
                        "log_returns",
                        "absolute_log_returns",
                    ],
                    "mode": "offline_retrospective",
                    "warning": (
                        "Historical structural break. "
                        "Not a live or future regime forecast."
                    ),
                },
            )
        )

    return detections
