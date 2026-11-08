"""Normal-distribution primitives backed by Python's numerical library."""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

from ._validation import finite_float

_STANDARD_NORMAL = NormalDist()


def normal_pdf(x: Any, *, mean: Any = 0.0, standard_deviation: Any = 1.0) -> float:
    """Evaluate the normal probability density function at ``x``."""
    value = finite_float(x, "x")
    mu = finite_float(mean, "mean")
    sigma = finite_float(standard_deviation, "standard_deviation")
    if sigma <= 0.0:
        raise ValueError("standard_deviation must be positive")
    z = (value - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2.0 * math.pi))


def normal_cdf(x: Any, *, mean: Any = 0.0, standard_deviation: Any = 1.0) -> float:
    """Evaluate the normal cumulative distribution function at ``x``."""
    value = finite_float(x, "x")
    mu = finite_float(mean, "mean")
    sigma = finite_float(standard_deviation, "standard_deviation")
    if sigma <= 0.0:
        raise ValueError("standard_deviation must be positive")
    return _STANDARD_NORMAL.cdf((value - mu) / sigma)


def normal_quantile(probability: Any, *, mean: Any = 0.0, standard_deviation: Any = 1.0) -> float:
    """Return the inverse normal CDF (quantile) for a probability in (0, 1)."""
    p = finite_float(probability, "probability")
    mu = finite_float(mean, "mean")
    sigma = finite_float(standard_deviation, "standard_deviation")
    if not 0.0 < p < 1.0:
        raise ValueError("probability must be strictly between 0 and 1")
    if sigma <= 0.0:
        raise ValueError("standard_deviation must be positive")
    return mu + sigma * _STANDARD_NORMAL.inv_cdf(p)
