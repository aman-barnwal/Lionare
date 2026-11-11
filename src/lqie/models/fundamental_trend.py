"""Experimental deterministic fundamental forecasting baseline.

This is an LQIE research baseline, not a validated market-price predictor.
"""

from __future__ import annotations

import numpy as np


def forecast_annual_metric(
    observations: list[dict],
    horizon: int = 3,
) -> dict:
    if not 1 <= horizon <= 5:
        raise ValueError("horizon must be between 1 and 5")

    points = []

    for item in observations:
        year = int(item["year"])
        value = float(item["value"])

        if np.isfinite(value):
            points.append((year, value))

    points.sort()

    if len(points) < 3:
        raise ValueError("At least 3 annual observations are required")

    years = np.array([p[0] for p in points], dtype=float)
    values = np.array([p[1] for p in points], dtype=float)

    if len(np.unique(years)) != len(years):
        raise ValueError("Duplicate annual observations")

    positive = bool(np.all(values > 0))

    if positive:
        target = np.log(values)
        coefficients = np.polyfit(years, target, 1)
        fitted = np.exp(np.polyval(coefficients, years))
        method = "Log-linear least-squares trend"
        future_values = np.exp(
            np.polyval(
                coefficients,
                np.arange(years[-1] + 1, years[-1] + 1 + horizon),
            )
        )
    else:
        coefficients = np.polyfit(years, values, 1)
        fitted = np.polyval(coefficients, years)
        method = "Linear least-squares trend"
        future_values = np.polyval(
            coefficients,
            np.arange(years[-1] + 1, years[-1] + 1 + horizon),
        )

    residuals = values - fitted
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    denominator = float(np.sum((values - values.mean()) ** 2))
    r_squared = (
        1.0 - float(np.sum(residuals ** 2)) / denominator
        if denominator > 0
        else None
    )

    forecasts = [
        {
            "year": int(year),
            "value": float(value),
            "unit": "USD",
        }
        for year, value in zip(
            range(int(years[-1]) + 1, int(years[-1]) + 1 + horizon),
            future_values,
        )
    ]

    return {
        "method": method,
        "observations_used": len(points),
        "history_start": int(years[0]),
        "history_end": int(years[-1]),
        "rmse_usd": rmse,
        "r_squared": r_squared,
        "forecasts": forecasts,
        "warning": (
            "Experimental historical fundamental trend. "
            "Not a share-price prediction, investment recommendation, "
            "or validated out-of-sample forecast."
        ),
    }
