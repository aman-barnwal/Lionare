"""Historical drawdown statistics."""

import math
from collections.abc import Sequence
from decimal import Decimal

Numeric = int | float | Decimal


def max_drawdown(prices: Sequence[Numeric]) -> float:
    """Return maximum peak-to-trough drawdown as a positive fraction.

    Example: a fall from 100 to 80 produces 0.20 (20%). Prices must be
    positive, finite, and supplied in chronological order.
    """
    if len(prices) < 2:
        raise ValueError("at least two prices are required")

    values: list[float] = []
    for item in prices:
        if isinstance(item, bool):
            raise TypeError("prices must be numeric, not bool")
        try:
            value = float(item)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("prices must be numeric") from exc
        if not math.isfinite(value) or value <= 0:
            raise ValueError("prices must be finite and strictly positive")
        values.append(value)

    peak = values[0]
    worst = 0.0
    for value in values[1:]:
        peak = max(peak, value)
        drawdown = (peak - value) / peak
        worst = max(worst, drawdown)
    return worst
