"""Historical and normal-parametric Value at Risk and Expected Shortfall."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any

import numpy as np

from ._validation import confidence_level, finite_float, return_series


@dataclass(frozen=True, slots=True)
class VaRCVaRResult:
    """Loss-side risk measures; positive values represent losses."""

    var: float
    cvar: float
    confidence: float
    observations: int
    method: str


def historical_var_cvar(returns: Any, *, confidence: float = 0.95) -> VaRCVaRResult:
    """Estimate historical VaR and CVaR from simple portfolio returns.

    Returns are converted to losses by ``loss = -return``. VaR uses NumPy's
    conservative ``higher`` empirical quantile. CVaR is the arithmetic mean
    of all observed losses greater than or equal to that VaR threshold. With
    tied observations this inclusive-tail convention can include more than
    exactly (1-confidence) of the sample; this is deliberate and disclosed.
    Positive results denote losses; negative VaR denotes a gain threshold.
    """
    alpha = confidence_level(confidence)
    values = return_series(returns)
    losses = -values
    var = float(np.quantile(losses, alpha, method="higher"))
    tail = losses[losses >= var]
    cvar = float(tail.mean())
    return VaRCVaRResult(var, cvar, alpha, int(values.size), "historical_higher_inclusive_tail")


def normal_var_cvar(
    mean_return: Any,
    volatility: Any,
    *,
    confidence: float = 0.95,
) -> VaRCVaRResult:
    """Compute normal-parametric loss VaR/CVaR from return mean and volatility.

    Assumes portfolio returns are normally distributed. ``volatility`` is the
    standard deviation over the same horizon as ``mean_return``. This is a
    modelling assumption, not a claim that real returns are normal.
    """
    alpha = confidence_level(confidence)
    mu = finite_float(mean_return, "mean_return")
    sigma = finite_float(volatility, "volatility")
    if sigma < 0.0:
        raise ValueError("volatility cannot be negative")
    z = NormalDist().inv_cdf(alpha)
    density = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    var = -mu + sigma * z
    cvar = -mu + sigma * density / (1.0 - alpha)
    return VaRCVaRResult(var, cvar, alpha, 0, "normal_parametric")
