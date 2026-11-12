# LQIE Run Manager

This utility runs the existing `scripts/run_lqie_patterns.py` from the Lionare repository and automatically archives each run.

## Install

Copy `scripts_lqie_run_manager.py` into the Lionare repository as `scripts/lqie_run_manager.py`.

## Run

From WSL Ubuntu, at `/mnt/c/lionare`, with the project virtual environment activated:

```bash
source venv/bin/activate
python scripts/lqie_run_manager.py \
  --file /tmp/lqie_synthetic_test.csv \
  --symbol SYNTHETIC_NVDA_TEST \
  --timeframe 1d \
  --run-tests all
```

Replace the synthetic CSV with a genuine OHLCV CSV or Parquet file for real market analysis. A synthetic file must remain labelled synthetic.

## Archive layout

The default root is `~/lionare-data/operations/lqie/`:

```text
operations/lqie/
├── history/                  # supplied 11 Nov baseline log + JSON summary
├── index.csv                 # one row per run
├── LATEST_RUN.txt            # path to newest run folder
└── runs/
    ├── <run-id>/             # complete folder for each run
    └── <run-id>.zip          # portable copy of that run
```

The first execution also creates `history/` and seeds it with your supplied 11 November 2026 smoke-test log plus a JSON baseline summary (73 full-suite tests passed; trendline detector had the pandas `DataFrame.append` error).

Each run is isolated. The CSV index provides a searchable history; `LATEST_RUN.txt` points to the most recent run. Test modes are `none`, `pattern`, and `all`. `all` runs the pattern tests, full pytest suite, and compile check.

The run manager does not change dependencies or patch third-party packages. It records the PyTrendline `DataFrame.append` compatibility warning so that the issue remains visible until explicitly fixed and retested.

## Included history

`history/lqie_initial_smoke_test_2026-11-11.log` is the log supplied with the request. It records the 73 passing tests and the PyTrendline `DataFrame.append` exception from the initial synthetic smoke test.
