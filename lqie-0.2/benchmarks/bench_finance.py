"""Reproducible microbenchmarks for LQIE's deterministic finance primitives.

Run from the repository root after installing the package:
    python benchmarks/bench_finance.py
    python benchmarks/bench_finance.py --iterations 500 --batches 7

These are local performance measurements, not accuracy tests or guarantees.
Compare runs only when machine, power mode, Python version, and workload match.
"""

from __future__ import annotations

import argparse
import math
import platform
import statistics
import sys
import time
from collections.abc import Callable

from lqie.finance import (
    annualized_volatility,
    calculate_valuation,
    log_returns,
    max_drawdown,
    simple_returns,
)


def build_workload(size: int = 1_000) -> tuple[list[float], list[float]]:
    """Create repeatable, positive price and return series without network I/O."""
    prices = [
        100.0 * math.exp(0.00005 * i + 0.012 * math.sin(i / 17.0))
        for i in range(size + 1)
    ]
    returns = simple_returns(prices)
    return prices, returns


def measure(
    label: str,
    operation: Callable[[], object],
    *,
    iterations: int,
    batches: int,
) -> dict[str, float | str | int]:
    """Return median per-call latency and throughput across repeated batches."""
    for _ in range(min(10, iterations)):
        operation()  # warm-up

    ns_per_call: list[float] = []
    for _ in range(batches):
        started = time.perf_counter_ns()
        for _ in range(iterations):
            operation()
        elapsed = time.perf_counter_ns() - started
        ns_per_call.append(elapsed / iterations)

    median_ns = statistics.median(ns_per_call)
    return {
        "benchmark": label,
        "iterations_per_batch": iterations,
        "batches": batches,
        "median_us_per_call": median_ns / 1_000,
        "median_calls_per_second": 1_000_000_000 / median_ns,
        "slowest_batch_us_per_call": max(ns_per_call) / 1_000,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()
    if args.iterations < 1 or args.batches < 2:
        parser.error("--iterations must be >= 1 and --batches must be >= 2")

    prices, returns = build_workload()

    # Correctness guards: never publish a speed result for a broken workload.
    valuation = calculate_valuation(
        shares_outstanding=100_000_000,
        share_price=50,
        total_debt=1_000_000_000,
        cash_and_equivalents=500_000_000,
    )
    assert valuation.market_cap == 5_000_000_000
    assert valuation.enterprise_value == 5_500_000_000
    assert len(log_returns(prices)) == len(prices) - 1
    assert 0.0 <= max_drawdown(prices) < 1.0
    assert annualized_volatility(returns) >= 0.0

    cases: list[tuple[str, Callable[[], object], int]] = [
        (
            "valuation_scalar",
            lambda: calculate_valuation(
                shares_outstanding=100_000_000,
                share_price=50,
                total_debt=1_000_000_000,
                cash_and_equivalents=500_000_000,
            ),
            max(args.iterations, 5_000),
        ),
        ("simple_returns_1000_periods", lambda: simple_returns(prices), args.iterations),
        ("log_returns_1000_periods", lambda: log_returns(prices), args.iterations),
        (
            "annualized_volatility_1000_periods",
            lambda: annualized_volatility(returns),
            args.iterations,
        ),
        ("max_drawdown_1000_periods", lambda: max_drawdown(prices), args.iterations),
    ]

    print("LQIE FINANCE MICROBENCHMARK")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Platform: {platform.platform()}")
    print(f"Workload: {len(prices) - 1} periods; batches: {args.batches}")
    print("Note: local microbenchmark; no pass/fail speed threshold.\n")
    print(f"{'Benchmark':43} {'Median us/call':>16} {'Calls/sec':>14} {'Slowest us':>13}")
    print("-" * 91)

    for label, operation, iterations in cases:
        result = measure(
            label,
            operation,
            iterations=iterations,
            batches=args.batches,
        )
        print(
            f"{result['benchmark']:43} "
            f"{result['median_us_per_call']:16.3f} "
            f"{result['median_calls_per_second']:14,.1f} "
            f"{result['slowest_batch_us_per_call']:13.3f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
