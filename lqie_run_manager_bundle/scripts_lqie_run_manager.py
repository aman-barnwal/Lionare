#!/usr/bin/env python3
"""LQIE run manager: execute analysis and archive every run in one organised folder.

Run from the Lionare repository root with the project's virtual environment active.
This script uses only the Python standard library; project dependencies are already
provided by the repository's virtual environment.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INITIAL_BASELINE_LOG = '(venv) ishendra@Aman-Barnwal077:/mnt/c/lionare$ cd /mnt/c/lionare\nsource venv/bin/activate\nset -euo pipefail\n\nexport PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"\n\necho "========== LQIE PATTERN TESTS =========="\npython -m pytest -v tests/test_pattern_engine.py\n\necho\necho "========== FULL LQIE TEST SUITE =========="\npython -m pytest -q\n\necho\necho "========== COMPILE CHECK =========="\npython -m compileall -q src/lqie scripts tests\n\necho\necho "========== PATTERN ENGINE IMPORT =========="\npython - <<\'PY\'\nfrom lqie.patterns import PatternEngine\nfrom lqie.features.pattern_features import build_pattern_feature_row\n\nprint("PatternEngine:", PatternEngine)\nprint("Feature builder:", build_pattern_feature_row)\nprint("LQIE pattern package ready.")\nPY\n========== LQIE PATTERN TESTS ==========\n=========================== test session starts ============================\nplatform linux -- Python 3.12.3, pytest-9.2.0, pluggy-1.7.0 -- /mnt/c/lionare/venv/bin/python\ncachedir: .pytest_cache\nrootdir: /mnt/c/lionare\nconfigfile: pytest.ini\nplugins: anyio-4.16.0, platformdirs-4.14.5\ncollected 7 items\n\ntests/test_pattern_engine.py::test_normalize_ohlcv PASSED            [ 14%]\ntests/test_pattern_engine.py::test_invalid_ohlc_rejected PASSED      [ 28%]\ntests/test_pattern_engine.py::test_duplicate_timestamps_rejected PASSED [ 42%]\ntests/test_pattern_engine.py::test_talib_bullish_engulfing_detection PASSED [ 57%]\ntests/test_pattern_engine.py::test_engine_calculates_indicators PASSED [ 71%]\ntests/test_pattern_engine.py::test_engine_returns_standardised_detections PASSED [ 85%]\ntests/test_pattern_engine.py::test_pattern_feature_generation PASSED [100%]\n\n============================ 7 passed in 22.02s ============================\n\n========== FULL LQIE TEST SUITE ==========\n.................................................................... [ 93%]\n.....                                                                [100%]\n73 passed in 58.68s\n\n========== COMPILE CHECK ==========\n\n========== PATTERN ENGINE IMPORT ==========\nPatternEngine: <class \'lqie.patterns.engine.PatternEngine\'>\nFeature builder: <function build_pattern_feature_row at 0x7c0bf40e0e00>\nLQIE pattern package ready.\n(venv) ishendra@Aman-Barnwal077:/mnt/c/lionare$ cd /mnt/c/lionare\nsource venv/bin/activate\nexport PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"\n\npython scripts/run_lqie_patterns.py \\\n  --file /path/to/your/market_candles.csv \\\n  --symbol NVDA \\\n  --timeframe 1d\nInput file not found: /path/to/your/market_candles.csv\nPS C:\\lionare> wsl\nishendra@Aman-Barnwal077:/mnt/c/lionare$\ncd /mnt/c/lionare\nsource venv/bin/activate\nset -euo pipefail\n\nexport PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"\n\necho "========== GENERATING SYNTHETIC TEST CANDLES =========="\n\npython - <<\'PY\'\nimport numpy as np\nimport pandas as pd\nfrom pathlib import Path\n\nrng = np.random.default_rng(42)\nn = 350\nx = np.arange(n)\n\nclose = (\n    100\n    + 0.06 * x\n    + 5 * np.sin(x / 8)\n    + 2 * np.sin(x / 23)\n    + rng.normal(0, 0.35, n)\n)\n\nopen_price = close + rng.normal(0, 0.4, n)\nhigh = np.maximum(open_price, close) + rng.uniform(0.1, 1.0, n)\nlow = np.minimum(open_price, close) - rng.uniform(0.1, 1.0, n)\n\n# Explicitly create a bullish engulfing example near the end.\nopen_price[-2], close[-2] = 112.0, 110.0\nhigh[-2], low[-2] = 113.0, 109.0\n\nopen_price[-1], close[-1] = 109.0, 114.0\nhigh[-1], low[-1] = 115.0, 108.0\n\nframe = pd.DataFrame({\n    "Date": pd.date_range(\n        "2025-01-01", periods=n, freq="D"\n    ),\necho "LQIE PATTERN ENGINE SMOKE TEST COMPLETE"==="===="is=1)).all())\n========== GENERATING SYNTHETIC TEST CANDLES ==========\nSynthetic test file: /tmp/lqie_synthetic_test.csv\nCandles: 350\nFirst candle: 2025-01-01 00:00:00\nLast candle: 2025-12-16 00:00:00\nOHLC validation: PASSED\n\n========== RUNNING ALL LQIE DETECTORS ==========\n========== LQIE 0.5 PATTERN ANALYSIS ==========\nSymbol: SYNTHETIC_NVDA_TEST\nTimeframe: 1d\nInput: /tmp/lqie_synthetic_test.csv\nBars: 350\ncandlesticks: 1 detections\ntrendlines ERROR: AttributeError: \'DataFrame\' object has no attribute \'append\'\nharmonics: 0 detections\nregimes: 0 detections\nDetection Parquet: /home/ishendra/lionare-data/gold/features/patterns/SYNTHETIC_NVDA_TEST_1d_20261111T163924Z.parquet\n\n========== RESULTS ==========\nBars analysed: 350\nLatest candle: 2025-12-16T00:00:00+00:00\nIndicators: 13\nPattern detections: 1\n[talib] engulfing | bullish | projected=False\n\nDetector errors: {\'trendlines\': {\'type\': \'AttributeError\', \'message\': "\'DataFrame\' object has no attribute \'append\'"}}\nJSON report: /home/ishendra/lionare-data/gold/features/patterns/SYNTHETIC_NVDA_TEST_1d_20261111T163924Z.json\nFeature report: /home/ishendra/lionare-data/gold/features/patterns/SYNTHETIC_NVDA_TEST_1d_20261111T163924Z_features.json\nWARNING: One or more detector engines reported errors.\n\n========== VERIFYING OUTPUT ==========\nSYNTHETIC_NVDA_TEST_1d_20261111T163924Z.parquet 8 KB\nSYNTHETIC_NVDA_TEST_1d_20261111T163924Z.json 4 KB\nSYNTHETIC_NVDA_TEST_1d_20261111T163924Z_features.json 4 KB\n\n========== FULL REGRESSION TESTS ==========\n.................................................................... [ 93%]\n.....                                                                [100%]\n73 passed in 77.35s (0:01:17)\n\nLQIE PATTERN ENGINE SMOKE TEST COMPLETE\n(venv) ishendra@Aman-Barnwal077:/mnt/c/lionare$ python - <<\'PY\'\nimport pathlib\nimport pytrendline\nimport pandas as pd\n\nroots = [\n    pathlib.Path("src/lqie/patterns/trendlines.py"),\n    pathlib.Path(pytrendline.__file__).resolve().parent,\n]\n\nprint("Pandas:", pd.__version__)\nprint("PyTrendline:", pytrendline.__file__)\nprint("\\n========== APPEND CALLS ==========")\n\nfor root in roots:\n    files = [root] if root.is_file() else list(root.rglob("*.py"))\n    for file in files:\n        try:\n            lines = file.read_text().splitlines()\n        except Exception:\n            continue\n\n        for i, line in enumerate(lines):\n            if ".append(" in line or ".append (" in line:\n                start = max(0, i - 2)\n                end = min(len(lines), i + 3)\n                print(f"\\n{file}:{i + 1}")\n                for n in range(start, end):\n                    print(f"{n + 1}: {lines[n]}")\nPY\nPandas: 3.1.1\nPyTrendline: /mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/__init__.py\n\n========== APPEND CALLS ==========\n\nsrc/lqie/patterns/trendlines.py:107\n105:             }\n106:\n107:             detections.append(\n108:                 PatternDetection(\n109:                     symbol=symbol.upper(),\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/detect.py:308\n306:           if abs(trend_price_at_k - pseries[k]) < max_allowable_error_pt_to_trend:\n307:             num_points += 1\n308:             points_in_trendline.append(k)\n309:             prices_in_trendline.append(trend_price_at_k)\n310:\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/detect.py:309\n307:             num_points += 1\n308:             points_in_trendline.append(k)\n309:             prices_in_trendline.append(trend_price_at_k)\n310:\n311:         # Check if we have the minimum required number of points for trend\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/detect.py:343\n341:           price_at_trendline = prices_in_trendline[w]\n342:           price_actual = pseries[point_index]\n343:           err_distances.append(abs(price_at_trendline - price_actual))\n344:\n345:         score = config.get("scoring_function", DEFAULT_CONFIG["scoring_function"])(candlestick_data, err_distances, num_points, slope)\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/detect.py:347\n345:         score = config.get("scoring_function", DEFAULT_CONFIG["scoring_function"])(candlestick_data, err_distances, num_points, slope)\n346:\n347:         trends_df = trends_df.append({\n348:           \'id\':              pointset_id,\n349:           \'trendtype\':       tt,\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/plot.py:87\n85:     pointset_indeces = []\n86:     for date in self.pointset_dates:\n87:       pointset_indeces.append( candles_df.loc[candles_df[\'Date\'] == date].index[0] )\n88:\n89:     pt_set_y = []\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/plot.py:94\n92:     for pt in pt_set_x:\n93:       if self.type == structs.TrendlineTypes.RESISTANCE:\n94:         pt_set_y.append(candles_df.iloc[pt].High)\n95:       elif self.type == structs.TrendlineTypes.SUPPORT:\n96:         pt_set_y.append(candles_df.iloc[pt].Low)\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/plot.py:96\n94:         pt_set_y.append(candles_df.iloc[pt].High)\n95:       elif self.type == structs.TrendlineTypes.SUPPORT:\n96:         pt_set_y.append(candles_df.iloc[pt].Low)\n97:       else:\n98:         pt_set_y.append(candles_df.iloc[pt].Low)\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/plot.py:98\n96:         pt_set_y.append(candles_df.iloc[pt].Low)\n97:       else:\n98:         pt_set_y.append(candles_df.iloc[pt].Low)\n99:\n100:     # Calculate slope and intersect using first point and last point\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/plot.py:226\n224:     pivot_panda_ts = candles_df.iloc[pivot_idx].name\n225:     pivot_y_val = candles_df.iloc[pivot_idx][col]\n226:     pivots_x_vals.append(pivot_panda_ts)\n227:     pivots_y_vals.append(pivot_y_val)\n228:   p.diamond(pivots_x_vals, pivots_y_vals, size=20, line_color="green", fill_alpha=0.1, alpha=0.5)\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/plot.py:227\n225:     pivot_y_val = candles_df.iloc[pivot_idx][col]\n226:     pivots_x_vals.append(pivot_panda_ts)\n227:     pivots_y_vals.append(pivot_y_val)\n228:   p.diamond(pivots_x_vals, pivots_y_vals, size=20, line_color="green", fill_alpha=0.1, alpha=0.5)\n229:\n\n/mnt/c/lionare/venv/lib/python3.12/site-packages/pytrendline/util.py:14\n12:   for idx, val in series.items():\n13:     if val == global_max_or_min or abs(global_max_or_min - val ) < tolerance_threshold:\n14:       isolated_globals.append(idx)\n15:   return isolated_globals\n16:\n(venv) ishendra@Aman-Barnwal077:/mnt/c/lionare$'

INITIAL_BASELINE_SUMMARY = {
    "recorded_date": "2026-11-11",
    "symbol": "SYNTHETIC_NVDA_TEST",
    "timeframe": "1d",
    "bars_analysed": 350,
    "latest_candle": "2025-12-16T00:00:00+00:00",
    "indicators": 13,
    "pattern_detections": 1,
    "detection": {"engine": "talib", "pattern": "engulfing", "direction": "bullish", "is_prediction": False},
    "detector_errors": [{"engine": "trendlines", "type": "AttributeError", "message": "'DataFrame' object has no attribute 'append'", "dependency_file": "pytrendline/detect.py", "reported_line": 347}],
    "tests": {"pattern_tests_passed": 7, "full_suite_passed": 73, "compile_check": "passed"},
    "status": "completed_with_detector_errors",
}

PACKAGE_NAMES = [
    "numpy", "pandas", "TA-Lib", "pytrendline", "ruptures", "mplfinance",
    "harmonic-patterns", "polars", "duckdb", "pyarrow", "pytest", "torch",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return value.strip("._-") or "UNKNOWN"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def run_logged(command: list[str], cwd: Path, env: dict[str, str], log_path: Path,
               tee: bool = True) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("COMMAND: " + " ".join(command) + "\n")
        log.write("CWD: " + str(cwd) + "\n\n")
        log.flush()
        proc = subprocess.Popen(
            command, cwd=str(cwd), env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            if tee:
                print(line, end="")
        return_code = proc.wait()
    return {
        "command": command,
        "return_code": return_code,
        "duration_seconds": round(time.monotonic() - started, 3),
        "log": str(log_path),
    }


def package_versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for package in PACKAGE_NAMES:
        try:
            out[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            out[package] = None
    return out


def git_info(repo: Path) -> dict[str, str | None]:
    result: dict[str, str | None] = {"commit": None, "branch": None, "working_tree": None}
    try:
        result["commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, stderr=subprocess.DEVNULL
        ).strip()
        result["branch"] = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=repo, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo, text=True, stderr=subprocess.DEVNULL
        ).strip()
        result["working_tree"] = "dirty" if dirty else "clean"
    except Exception:
        pass
    return result


def pytrendline_diagnostic() -> dict[str, Any]:
    """Detect the known pandas DataFrame.append incompatibility without patching packages."""
    data: dict[str, Any] = {
        "pandas_version": None,
        "pytrendline_version": None,
        "detect_module": None,
        "legacy_dataframe_append_found": False,
        "matching_lines": [],
        "status": "not_checked",
    }
    try:
        data["pandas_version"] = metadata.version("pandas")
        data["pytrendline_version"] = metadata.version("pytrendline")
        import pytrendline  # type: ignore
        detect_file = Path(pytrendline.__file__).resolve().parent / "detect.py"
        data["detect_module"] = str(detect_file)
        if detect_file.exists():
            for number, line in enumerate(detect_file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(r"\b\w+\s*=\s*\w+\.append\s*\(", line):
                    data["matching_lines"].append({"line": number, "code": line.strip()})
            data["legacy_dataframe_append_found"] = any(
                "trends_df.append(" in item["code"] for item in data["matching_lines"]
            )
        data["status"] = "compatibility_warning" if data["legacy_dataframe_append_found"] else "no_known_append_call_found"
    except Exception as exc:
        data["status"] = "diagnostic_unavailable"
        data["error"] = f"{type(exc).__name__}: {exc}"
    return data


def parse_engine_output(output: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "bars_analysed": None,
        "latest_candle": None,
        "indicators": None,
        "pattern_detections": None,
        "detector_errors": [],
        "generated_files": {},
    }
    patterns = {
        "bars_analysed": r"Bars analysed:\s*(\d+)",
        "latest_candle": r"Latest candle:\s*(.+)",
        "indicators": r"Indicators:\s*(\d+)",
        "pattern_detections": r"Pattern detections:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if match:
            parsed[key] = int(match.group(1)) if key in {"bars_analysed", "indicators", "pattern_detections"} else match.group(1).strip()

    for label, pattern in {
        "detection_parquet": r"Detection Parquet:\s*(.+)",
        "json_report": r"JSON report:\s*(.+)",
        "feature_report": r"Feature report:\s*(.+)",
    }.items():
        match = re.search(pattern, output)
        if match:
            parsed["generated_files"][label] = match.group(1).strip()

    for line in output.splitlines():
        if "trendlines ERROR:" in line or "harmonics ERROR:" in line or "regimes ERROR:" in line or "candlesticks ERROR:" in line:
            parsed["detector_errors"].append(line.strip())
    error_obj = re.search(r"Detector errors:\s*(\{.*\})", output)
    if error_obj and not parsed["detector_errors"]:
        parsed["detector_errors"].append(error_obj.group(1))
    return parsed


def copy_generated_reports(parsed: dict[str, Any], report_dir: Path) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    report_dir.mkdir(parents=True, exist_ok=True)
    for kind, raw_path in parsed.get("generated_files", {}).items():
        src = Path(raw_path).expanduser()
        if src.exists() and src.is_file():
            dst = report_dir / f"{kind}_{src.name}"
            shutil.copy2(src, dst)
            copied.append({"type": kind, "source": str(src), "archived": str(dst)})
        else:
            copied.append({"type": kind, "source": str(src), "archived": "NOT_FOUND"})
    return copied


def run_validation(repo: Path, env: dict[str, str], log_dir: Path, mode: str) -> dict[str, Any]:
    if mode == "none":
        return {"mode": mode, "status": "not_requested", "checks": []}
    checks: list[dict[str, Any]] = []
    commands: list[tuple[str, list[str]]] = []
    if mode in {"pattern", "all"}:
        commands.append(("pattern_tests", [sys.executable, "-m", "pytest", "-v", "tests/test_pattern_engine.py"]))
    if mode == "all":
        commands.append(("full_test_suite", [sys.executable, "-m", "pytest", "-q"]))
        commands.append(("compile_check", [sys.executable, "-m", "compileall", "-q", "src/lqie", "scripts", "tests"]))
    for name, command in commands:
        item = run_logged(command, repo, env, log_dir / f"{name}.log")
        item["name"] = name
        checks.append(item)
    return {
        "mode": mode,
        "status": "passed" if all(c["return_code"] == 0 for c in checks) else "failed",
        "checks": checks,
    }


def install_initial_history(root: Path) -> None:
    """Seed the central archive with the initial smoke-test log supplied by the user."""
    history = root / "history"
    history.mkdir(parents=True, exist_ok=True)
    log_path = history / "lqie_initial_smoke_test_2026-11-11.log"
    summary_path = history / "lqie_initial_smoke_test_2026-11-11.json"
    if not log_path.exists():
        log_path.write_text(INITIAL_BASELINE_LOG, encoding="utf-8")
    if not summary_path.exists():
        write_json(summary_path, INITIAL_BASELINE_SUMMARY)


def append_index(index_path: Path, row: dict[str, Any]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["run_id", "started_utc", "symbol", "timeframe", "status", "bars_analysed", "pattern_detections", "run_folder"]
    exists = index_path.exists()
    with index_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def create_zip(run_dir: Path) -> Path:
    zip_path = run_dir.parent / f"{run_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file in run_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(run_dir.parent))
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LQIE and automatically archive all run artefacts.")
    parser.add_argument("--file", required=True, help="CSV or Parquet file containing OHLCV candles")
    parser.add_argument("--symbol", required=True, help="Symbol or synthetic test label")
    parser.add_argument("--timeframe", default="1d", help="Candle timeframe (default: 1d)")
    parser.add_argument("--run-tests", choices=["none", "pattern", "all"], default="none",
                        help="Also archive tests: pattern only, or pattern + full suite + compile check")
    parser.add_argument("--output-root", default=str(Path.home() / "lionare-data" / "operations" / "lqie"),
                        help="Archive root (default: ~/lionare-data/operations/lqie)")
    parser.add_argument("--no-zip", action="store_true", help="Do not create a ZIP copy of the run folder")
    args = parser.parse_args()

    repo = Path.cwd().resolve()
    input_file = Path(args.file).expanduser().resolve()
    runner = repo / "scripts" / "run_lqie_patterns.py"
    if not input_file.is_file():
        parser.error(f"Input file does not exist: {input_file}")
    if not runner.is_file():
        parser.error(f"Run this from the Lionare repository root; missing: {runner}")

    started = utc_now()
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    symbol = safe_name(args.symbol.upper())
    timeframe = safe_name(args.timeframe)
    run_id = f"{stamp}_{symbol}_{timeframe}"
    root = Path(args.output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    install_initial_history(root)
    runs_root = root / "runs"
    run_dir = runs_root / run_id
    if run_dir.exists():
        suffix = 2
        while (runs_root / f"{run_id}_{suffix}").exists():
            suffix += 1
        run_id = f"{run_id}_{suffix}"
        run_dir = runs_root / run_id

    for folder in ["input", "reports", "logs", "diagnostics", "metadata"]:
        (run_dir / folder).mkdir(parents=True, exist_ok=True)

    archived_input = run_dir / "input" / input_file.name
    shutil.copy2(input_file, archived_input)
    input_meta = {
        "original_path": str(input_file),
        "archived_path": str(archived_input),
        "size_bytes": archived_input.stat().st_size,
        "sha256": sha256_file(archived_input),
    }

    env = os.environ.copy()
    src_path = str(repo / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    print(f"\nLQIE run: {run_id}")
    print(f"Archive:  {run_dir}")
    print(f"Input:    {archived_input}\n")

    engine_cmd = [sys.executable, str(runner), "--file", str(archived_input),
                  "--symbol", args.symbol, "--timeframe", args.timeframe]
    engine_result = run_logged(engine_cmd, repo, env, run_dir / "logs" / "pattern_engine.log")
    output_text = (run_dir / "logs" / "pattern_engine.log").read_text(encoding="utf-8", errors="replace")
    parsed = parse_engine_output(output_text)
    copied_reports = copy_generated_reports(parsed, run_dir / "reports")

    validation = run_validation(repo, env, run_dir / "logs", args.run_tests)
    diagnostic = pytrendline_diagnostic()
    write_json(run_dir / "diagnostics" / "pytrendline_pandas_compatibility.json", diagnostic)

    if engine_result["return_code"] != 0:
        status = "run_failed"
    elif parsed["detector_errors"] or diagnostic.get("legacy_dataframe_append_found"):
        status = "completed_with_detector_errors"
    else:
        status = "completed"
    if validation["status"] == "failed":
        status = "validation_failed" if status == "completed" else status + "_and_validation_failed"

    finished = utc_now()
    metadata_doc = {
        "run_id": run_id,
        "status": status,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "input": input_meta,
        "engine": engine_result,
        "analysis_summary": parsed,
        "archived_reports": copied_reports,
        "validation": validation,
        "environment": {
            "python_version": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "packages": package_versions(),
            "git": git_info(repo),
        },
        "diagnostics": diagnostic,
    }
    write_json(run_dir / "metadata" / "run.json", metadata_doc)

    checksums: dict[str, str] = {}
    for file in sorted(run_dir.rglob("*")):
        if file.is_file() and file.name != "checksums.json":
            checksums[str(file.relative_to(run_dir))] = sha256_file(file)
    write_json(run_dir / "metadata" / "checksums.json", checksums)

    summary = [
        f"# LQIE Run — {run_id}", "", f"- **Status:** `{status}`",
        f"- **Symbol:** `{args.symbol}`", f"- **Timeframe:** `{args.timeframe}`",
        f"- **Started (UTC):** {started.isoformat()}",
        f"- **Input bars analysed:** {parsed.get('bars_analysed')}",
        f"- **Latest candle:** {parsed.get('latest_candle')}",
        f"- **Indicators:** {parsed.get('indicators')}",
        f"- **Pattern detections:** {parsed.get('pattern_detections')}",
        f"- **Engine exit code:** {engine_result['return_code']}",
        f"- **Validation:** {validation['status']} ({validation['mode']})", "",
        "## Detector errors", "",
    ]
    summary += [f"- {error}" for error in parsed["detector_errors"]] or ["- None reported by the runner."]
    summary += ["", "## PyTrendline / pandas compatibility", "",
                f"- Pandas: `{diagnostic.get('pandas_version')}`",
                f"- PyTrendline: `{diagnostic.get('pytrendline_version')}`",
                f"- Status: `{diagnostic.get('status')}`"]
    for match in diagnostic.get("matching_lines", []):
        summary.append(f"- Legacy append call at line {match['line']}: `{match['code']}`")
    summary += ["", "## Folder contents", "",
                "- `input/` — copied input snapshot used for this run",
                "- `reports/` — JSON, feature JSON, and detection Parquet copied from LQIE",
                "- `logs/` — engine output and optional test/compile logs",
                "- `diagnostics/` — dependency compatibility checks",
                "- `metadata/run.json` — complete machine-readable run record",
                "- `metadata/checksums.json` — SHA-256 checksums for archived files", ""]
    (run_dir / "summary.md").write_text("\n".join(summary), encoding="utf-8")

    index_row = {
        "run_id": run_id, "started_utc": started.isoformat(), "symbol": args.symbol,
        "timeframe": args.timeframe, "status": status,
        "bars_analysed": parsed.get("bars_analysed"),
        "pattern_detections": parsed.get("pattern_detections"), "run_folder": str(run_dir),
    }
    append_index(root / "index.csv", index_row)
    (root / "LATEST_RUN.txt").write_text(str(run_dir) + "\n", encoding="utf-8")

    zip_path = None if args.no_zip else create_zip(run_dir)
    print("\n========== LQIE ARCHIVE COMPLETE ==========")
    print("Status:", status)
    print("Run folder:", run_dir)
    print("Summary:", run_dir / "summary.md")
    print("Index:", root / "index.csv")
    if zip_path:
        print("ZIP:", zip_path)
    if parsed["detector_errors"]:
        print("NOTE: Detector errors are preserved in the logs and metadata; no detector code was silently modified.")
    return 0 if engine_result["return_code"] == 0 else engine_result["return_code"]


if __name__ == "__main__":
    raise SystemExit(main())
