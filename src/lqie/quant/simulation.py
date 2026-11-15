"""Numerical Monte Carlo simulations for geometric Brownian motion."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ._validation import finite_float


def simulate_gbm_paths(
    *,
    initial_price: Any,
    annual_drift: Any,
    annual_volatility: Any,
    time_horizon_years: Any,
    steps: int = 252,
    n_paths: int = 10_000,
    seed: int | None = 42,
) -> np.ndarray:
    """Simulate geometric-Brownian-motion price paths.

    Returns an ndarray shaped ``(n_paths, steps + 1)`` including initial price.
    Uses exact GBM transitions under constant drift and volatility. This is a
    baseline stochastic model, not a calibrated market forecast.
    """
    s0 = finite_float(initial_price, "initial_price")
    mu = finite_float(annual_drift, "annual_drift")
    sigma = finite_float(annual_volatility, "annual_volatility")
    horizon = finite_float(time_horizon_years, "time_horizon_years")
    if s0 <= 0.0:
        raise ValueError("initial_price must be positive")
    if sigma < 0.0:
        raise ValueError("annual_volatility cannot be negative")
    if horizon <= 0.0:
        raise ValueError("time_horizon_years must be positive")
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("steps must be a positive integer")
    if isinstance(n_paths, bool) or not isinstance(n_paths, int) or n_paths < 1:
        raise ValueError("n_paths must be a positive integer")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError("seed must be an integer or None")

    dt = horizon / steps
    rng = np.random.default_rng(seed)
    shocks = rng.standard_normal((n_paths, steps))
    increments = (mu - 0.5 * sigma * sigma) * dt + sigma * math.sqrt(dt) * shocks
    log_paths = np.cumsum(increments, axis=1)
    paths = np.empty((n_paths, steps + 1), dtype=np.float64)
    paths[:, 0] = s0
    paths[:, 1:] = s0 * np.exp(log_paths)
    if not np.all(np.isfinite(paths)):
        raise FloatingPointError("simulation overflowed; check drift, volatility, and horizon")
    return paths
