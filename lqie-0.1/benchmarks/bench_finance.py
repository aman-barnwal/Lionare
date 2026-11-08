import argparse
import math
import platform
import statistics
import time

from lqie.finance import (
    calculate_valuation,
    simple_returns,
    log_returns,
    annualized_volatility,
    max_drawdown,
)

def workload(n=1000):
    prices = [
        100 * math.exp(0.00005 * i + 0.012 * math.sin(i / 17))
        for i in range(n + 1)
    ]
    returns = simple_returns(prices)
    return prices, returns

def benchmark(name, fn, iterations, batches):
    for _ in range(10):
        fn()

    times = []

    for _ in range(batches):
        start = time.perf_counter()
        for _ in range(iterations):
            fn()
        elapsed = time.perf_counter() - start
        times.append(elapsed / iterations * 1_000_000)

    median = statistics.median(times)

    print(
        f"{name:34} "
        f"{median:12.3f} us "
        f"{1_000_000 / median:14,.1f} ops/sec"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()

    if args.iterations < 1 or args.batches < 2:
        parser.error("iterations >= 1 and batches >= 2 required")

    prices, returns = workload()

    valuation = lambda: calculate_valuation(
        shares_outstanding=100_000_000,
        share_price=50,
        total_debt=1_000_000_000,
        cash_and_equivalents=500_000_000,
    )

    assert valuation().market_cap == 5_000_000_000
    assert valuation().enterprise_value == 5_500_000_000

    cases = [
        ("Valuation", valuation, max(args.iterations, 5000)),
        ("Simple returns (1000 periods)", lambda: simple_returns(prices), args.iterations),
        ("Log returns (1000 periods)", lambda: log_returns(prices), args.iterations),
        ("Annualized volatility", lambda: annualized_volatility(returns), args.iterations),
        ("Maximum drawdown", lambda: max_drawdown(prices), args.iterations),
    ]

    print("\n========== LQIE PERFORMANCE BENCHMARK ==========")
    print("Python:", platform.python_version())
    print("Platform:", platform.platform())
    print("Iterations:", args.iterations, "| Batches:", args.batches)
    print("-" * 70)
    print(f"{'Operation':34} {'Latency':>12} {'Throughput':>16}")
    print("-" * 70)

    for name, fn, iterations in cases:
        benchmark(name, fn, iterations, args.batches)

    print("-" * 70)
    print("Benchmark completed. No speed threshold is assumed.")

if __name__ == "__main__":
    main()
