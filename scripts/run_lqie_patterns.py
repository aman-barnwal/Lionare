"""Run LQIE pattern analysis against a CSV or Parquet OHLCV file."""

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from lqie.data.lake import LakePaths, write_parquet
from lqie.features.pattern_features import build_pattern_feature_row
from lqie.patterns import PatternEngine


def main():
    parser = argparse.ArgumentParser(
        description="Run LQIE 0.5 pattern analysis."
    )

    parser.add_argument("--file", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1d")
    parser.add_argument("--skip-trendlines", action="store_true")
    parser.add_argument("--skip-harmonics", action="store_true")
    parser.add_argument("--skip-regimes", action="store_true")

    args = parser.parse_args()

    source = Path(args.file).expanduser().resolve()

    if not source.is_file():
        raise SystemExit(f"Input file not found: {source}")

    if source.suffix.lower() == ".parquet":
        data = pl.read_parquet(source)
    elif source.suffix.lower() == ".csv":
        data = pl.read_csv(source, try_parse_dates=True)
    else:
        raise SystemExit("Input must be CSV or Parquet.")

    print("========== LQIE 0.5 PATTERN ANALYSIS ==========")
    print("Symbol:", args.symbol.upper())
    print("Timeframe:", args.timeframe)
    print("Input:", source)
    print("Bars:", data.height)

    engine = PatternEngine()

    result = engine.analyze(
        data,
        symbol=args.symbol,
        timeframe=args.timeframe,
        include_trendlines=not args.skip_trendlines,
        include_harmonics=not args.skip_harmonics,
        include_regimes=not args.skip_regimes,
    )

    root = LakePaths().ensure()
    output_dir = root.gold / "features" / "patterns"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    safe_symbol = re.sub(
        r"[^A-Za-z0-9_-]", "_", args.symbol.upper()
    )
    safe_timeframe = re.sub(
        r"[^A-Za-z0-9_-]", "_", args.timeframe
    )
    stem = f"{safe_symbol}_{safe_timeframe}_{timestamp}"

    json_path = output_dir / f"{stem}.json"

    json_path.write_text(
        json.dumps(result, indent=2, default=str),
        encoding="utf-8",
    )

    if result["detections"]:
        rows = []

        for item in result["detections"]:
            record = {
                key: value
                for key, value in item.items()
                if key != "metadata"
            }

            record["metadata_json"] = json.dumps(
                item["metadata"],
                default=str,
            )

            rows.append(record)

        parquet_path = output_dir / f"{stem}.parquet"

        write_parquet(
            pl.DataFrame(rows, infer_schema_length=None),
            parquet_path,
        )

        print("Detection Parquet:", parquet_path)

    feature_row = build_pattern_feature_row(result)

    features_path = output_dir / f"{stem}_features.json"

    features_path.write_text(
        json.dumps(feature_row, indent=2, default=str),
        encoding="utf-8",
    )

    print("\n========== RESULTS ==========")
    print("Bars analysed:", result["bars_analysed"])
    print("Latest candle:", result["last_bar"])
    print("Indicators:", len(result["indicators"]))
    print("Pattern detections:", result["detection_count"])

    for item in result["detections"]:
        print(
            f"[{item['engine']}] {item['pattern']} "
            f"| {item['direction']} "
            f"| projected={item['is_prediction']}"
        )

    print("\nDetector errors:", result["errors"])
    print("JSON report:", json_path)
    print("Feature report:", features_path)

    if result["errors"]:
        print("WARNING: One or more detector engines reported errors.")


if __name__ == "__main__":
    main()
