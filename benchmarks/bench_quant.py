"""Reproducible microbenchmarks for LQIE 0.2 numerical operations.

These are local microbenchmarks, not production throughput guarantees. Keep
hardware, Python/NumPy versions, inputs, and flags fixed when comparing runs.
"""

from __future__ import annotations

import argparse
import platform
import statistics
import time

import numpy as np

from lqie.quant import (
    correlation_matrix,
    covariance_matrix,
    fit_ols,
    historical_var_cvar,
    normal_var_cvar,
    simulate_gbm_paths,
)


def measure(name: str, fn, iterations: int, batches: int) -> None:
    for _ in range(3):
        fn()
    batch_us = []
    for _ in range(batches):
        start = time.perf_counter()
        for _ in range(iterations):
            fn()
        batch_us.append((time.perf_counter() - start) * 1e6 / iterations)
    median_us = statistics.median(batch_us)
    spread_us = max(batch_us) - min(batch_us)
    print(f"{name:34} {median_us:12.3f} us  spread {spread_us:10.3f} us  {1e6 / median_us:12,.1f} ops/s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()
    if args.iterations < 1 or args.batches < 2:
        parser.error("iterations must be >= 1 and batches must be >= 2")

    rng = np.random.default_rng(20261108)
    observations = 5_000
    assets = {f"asset_{i:02d}": rng.normal(0.0003, 0.015 + i * 0.0002, observations) for i in range(10)}
    returns = rng.normal(0.0002, 0.012, observations)
    x = rng.normal(size=(observations, 5))
    y = 0.4 + x @ np.array([0.2, -0.1, 0.3, 0.05, -0.2]) + rng.normal(0, 0.2, observations)

    covariance_fn = lambda: covariance_matrix(assets)
    correlation_fn = lambda: correlation_matrix(assets)
    regression_fn = lambda: fit_ols(y, x)
    historical_risk_fn = lambda: historical_var_cvar(returns)
    normal_risk_fn = lambda: normal_var_cvar(float(returns.mean()), float(returns.std(ddof=1)))
    simulation_fn = lambda: simulate_gbm_paths(
        initial_price=100.0, annual_drift=0.07, annual_volatility=0.22,
        time_horizon_years=1.0, steps=252, n_paths=1_000, seed=2026,
    )

    simulation_iterations = max(1, args.iterations // 20)
    print("\n========== LQIE 0.2 QUANT BENCHMARK ==========")
    print(f"Python: {platform.python_version()} | NumPy: {np.__version__}")
    print(f"Platform: {platform.platform()}")
    print(f"Assets: 10 | Observations: {observations} | Batches: {args.batches}")
    print("Latency is per complete operation; simulations use fewer repetitions.")
    print("-" * 112)
    measure("Covariance matrix (10 assets)", covariance_fn, args.iterations, args.batches)
    measure("Correlation matrix (10 assets)", correlation_fn, args.iterations, args.batches)
    measure("OLS (5,000 x 5)", regression_fn, args.iterations, args.batches)
    measure("Historical VaR/CVaR (5,000)", historical_risk_fn, args.iterations, args.batches)
    measure("Normal VaR/CVaR", normal_risk_fn, args.iterations, args.batches)
    measure("GBM (1,000 paths x 252 steps)", simulation_fn, simulation_iterations, args.batches)
    print("-" * 112)
    print("Completed. Compare on the same machine and software environment.")


if __name__ == "__main__":
    main()
