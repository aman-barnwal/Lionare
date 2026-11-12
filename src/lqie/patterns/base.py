"""Input validation and canonical OHLCV normalisation."""

import numpy as np
import pandas as pd


def normalize_ohlcv(data) -> pd.DataFrame:
    """
    Accept a Pandas/Polars DataFrame or record collection.

    Returns columns:
    Datetime, Open, High, Low, Close, Volume.
    Datetimes are UTC and sorted ascending.
    """
    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    elif hasattr(data, "to_pandas"):
        frame = data.to_pandas()
    else:
        frame = pd.DataFrame(data)

    if frame.empty:
        raise ValueError("OHLCV input is empty")

    aliases = {
        str(column).strip().lower(): column
        for column in frame.columns
    }

    def find_column(names):
        for name in names:
            if name in aliases:
                return aliases[name]
        return None

    date_col = find_column(
        ["datetime", "timestamp", "date", "time"]
    )

    if date_col is None:
        raise ValueError(
            "Missing date/time column. Expected Date, Datetime or Timestamp."
        )

    required = {
        "Open": find_column(["open"]),
        "High": find_column(["high"]),
        "Low": find_column(["low"]),
        "Close": find_column(["close"]),
    }

    missing = [name for name, col in required.items() if col is None]
    if missing:
        raise ValueError(f"Missing OHLC columns: {missing}")

    raw_datetime = frame[date_col]

    if pd.api.types.is_numeric_dtype(raw_datetime):
        numeric = pd.to_numeric(raw_datetime, errors="coerce")
        median = numeric.dropna().abs().median()

        if median >= 1e12:
            unit = "ms"
        elif median >= 1e9:
            unit = "s"
        else:
            raise ValueError(
                "Numeric timestamps must use Unix seconds or milliseconds."
            )

        timestamps = pd.to_datetime(
            numeric, unit=unit, utc=True, errors="coerce"
        )
    else:
        timestamps = pd.to_datetime(
            raw_datetime, utc=True, errors="coerce"
        )

    result = pd.DataFrame({
        "Datetime": timestamps,
        **{
            name: pd.to_numeric(frame[col], errors="coerce")
            for name, col in required.items()
        },
    })

    volume_col = find_column(["volume"])
    result["Volume"] = (
        pd.to_numeric(frame[volume_col], errors="coerce")
        if volume_col is not None
        else 0.0
    )

    if result.isna().any().any():
        raise ValueError(
            "OHLCV data contains missing or invalid values."
        )

    prices = result[["Open", "High", "Low", "Close"]].to_numpy(
        dtype=np.float64
    )
    volume = result["Volume"].to_numpy(dtype=np.float64)

    if not np.isfinite(prices).all() or not np.isfinite(volume).all():
        raise ValueError("OHLCV contains non-finite numeric values.")

    if (prices <= 0).any():
        raise ValueError("OHLC prices must be positive.")

    if (volume < 0).any():
        raise ValueError("Volume cannot be negative.")

    if (
        result["High"] < result[["Open", "Close"]].max(axis=1)
    ).any():
        raise ValueError("Invalid OHLC: High is below Open or Close.")

    if (
        result["Low"] > result[["Open", "Close"]].min(axis=1)
    ).any():
        raise ValueError("Invalid OHLC: Low is above Open or Close.")

    if (result["Low"] > result["High"]).any():
        raise ValueError("Invalid OHLC: Low exceeds High.")

    result = result.sort_values("Datetime").reset_index(drop=True)

    if result["Datetime"].duplicated().any():
        raise ValueError("Duplicate candle timestamps.")

    if len(result) < 3:
        raise ValueError("At least three candles are required.")

    return result
