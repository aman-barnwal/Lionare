"""Basic return and volatility calculations for ordered price observations."""

import math
import statistics
from collections.abc import Sequence
from decimal import Decimal

Numeric = int | float | Decimal


def _finite_float(value: Numeric, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric, not bool")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _prices(values: Sequence[Numeric]) -> list[float]:
    if len(values) < 2:
        raise ValueError("at least two prices are required")
    converted = [_finite_float(value, "price") for value in values]
    if any(value <= 0 for value in converted):
        raise ValueError("prices must be strictly positive")
    return converted


def simple_returns(prices: Sequence[Numeric]) -> list[float]:
    """Return period-over-period simple returns: P[t] / P[t-1] - 1."""
    values = _prices(prices)
    return [current / previous - 1.0 for previous, current in zip(values, values[1:])]


def log_returns(prices: Sequence[Numeric]) -> list[float]:
    """Return continuously compounded returns: ln(P[t] / P[t-1])."""
    values = _prices(prices)
    return [math.log(current / previous) for previous, current in zip(values, values[1:])]


def annualized_volatility(
    returns: Sequence[Numeric], *, periods_per_year: int = 252
) -> float:
    """Annualize sample standard deviation of periodic returns.

    Assumes equally spaced observations and the supplied periods_per_year
    convention (252 for typical daily trading observations). This is a
    historical estimator, not a forecast.
    """
    if isinstance(periods_per_year, bool) or not isinstance(periods_per_year, int):
        raise TypeError("periods_per_year must be an integer")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if len(returns) < 2:
        raise ValueError("at least two returns are required for sample volatility")

    values = [_finite_float(value, "return") for value in returns]
    if any(value <= -1.0 for value in values):
        raise ValueError("simple returns must be greater than -1")
    return statistics.stdev(values) * math.sqrt(periods_per_year)
