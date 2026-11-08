import argparse
import statistics
import time
from datetime import date, timedelta

from lqie.data.schema import normalize_ohlcv_records


def generate_records(count):
    start = date(2000, 1, 1)
    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "open": 100.0 + i * 0.001,
            "high": 101.0 + i * 0.001,
            "low": 99.0 + i * 0.001,
            "close": 100.5 + i * 0.001,
            "volume": 1_000_000 + i,
        }
        for i in range(count)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()

    if args.rows < 1 or args.iterations < 1 or args.batches < 2:
        parser.error("rows and iterations must be positive; batches >= 2")

    records = generate_records(args.rows)
    times = []

    for _ in range(args.batches):
        start = time.perf_counter()

        for _ in range(args.iterations):
            result = normalize_ohlcv_records(
                "SPY", records, "synthetic-benchmark"
            )

        times.append(
            (time.perf_counter() - start) / args.iterations
        )

    median = statistics.median(times)

    print("========== LQIE DATA BENCHMARK ==========")
    print("Rows per operation:", args.rows)
    print("Batches:", args.batches)
    print(f"Median latency: {median * 1000:.3f} ms")
    print(f"Throughput: {args.rows / median:,.0f} rows/sec")
    print("Output rows:", len(result))
    print("NOTE: Synthetic in-memory normalization benchmark.")


if __name__ == "__main__":
    main()
