from dataclasses import dataclass
from datetime import date, datetime, timezone
import math


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str
    retrieved_at_utc: datetime


def _parse_date(value):
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return date.fromisoformat(str(value)[:10])


def normalize_ohlcv_records(
    symbol,
    records,
    source,
    retrieved_at=None,
):
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol cannot be empty")

    if not source:
        raise ValueError("source cannot be empty")

    retrieved_at = retrieved_at or datetime.now(timezone.utc)

    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")

    required = {"date", "open", "high", "low", "close", "volume"}
    normalized = []
    seen_dates = set()

    for index, row in enumerate(records):
        row = {str(k).lower(): v for k, v in row.items()}

        missing = required - row.keys()
        if missing:
            raise ValueError(f"Row {index}: missing fields {missing}")

        try:
            day = _parse_date(row["date"])
            o, h, l, c = (
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
            )
            volume_float = float(row["volume"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Row {index}: invalid numeric/date data") from exc

        values = (o, h, l, c, volume_float)

        if not all(math.isfinite(v) for v in values):
            raise ValueError(f"Row {index}: non-finite values")

        if min(o, h, l, c) <= 0:
            raise ValueError(f"Row {index}: prices must be positive")

        if l > min(o, c) or h < max(o, c) or l > h:
            raise ValueError(f"Row {index}: invalid OHLC relationship")

        if volume_float < 0 or not volume_float.is_integer():
            raise ValueError(f"Row {index}: invalid volume")

        if day in seen_dates:
            raise ValueError(f"Duplicate observation date: {day}")

        seen_dates.add(day)

        normalized.append(
            OHLCVBar(
                date=day,
                symbol=symbol,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=int(volume_float),
                source=str(source),
                retrieved_at_utc=retrieved_at,
            )
        )

    if not normalized:
        raise ValueError("No observations received")

    return sorted(normalized, key=lambda item: item.date)
